import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app_ai_core import verify_vehicle_exists
from competitors import get_competitors
from fetch_marketcheck import MarketCheckError, search_by_criteria
from fetch_recalls import get_live_recalls
from vehicle_reference_image import resolve_vehicle_photo

MAX_RECALL_YEARS = 4
RECALL_FETCH_WORKERS = 3
RECALL_FETCH_TIMEOUT = 12

USE_CASE_MODELS: dict[str, list[dict[str, str]]] = {
    "outdoors": [
        {"make": "Toyota", "model": "Tacoma", "angle": "Midsize truck with strong off-road trims and resale value."},
        {"make": "Jeep", "model": "Wrangler", "angle": "Purpose-built for trails, removable top, iconic outdoor lifestyle."},
        {"make": "Subaru", "model": "Outback", "angle": "Standard AWD wagon with camping-friendly practicality."},
        {"make": "Ford", "model": "Bronco", "angle": "Dedicated off-roader with removable doors and 4x4 hardware."},
    ],
    "large_family": [
        {"make": "Toyota", "model": "Highlander", "angle": "Three-row reliability with strong family resale."},
        {"make": "Honda", "model": "Pilot", "angle": "Spacious third row and family-friendly packaging."},
        {"make": "Kia", "model": "Telluride", "angle": "Upscale three-row value with long warranty."},
        {"make": "Chevrolet", "model": "Traverse", "angle": "Very roomy cabin for large households."},
    ],
    "fuel_economy": [
        {"make": "Toyota", "model": "Corolla", "angle": "Conservative ownership costs and high MPG."},
        {"make": "Honda", "model": "Civic", "angle": "Efficient compact with broad trim choice."},
        {"make": "Hyundai", "model": "Elantra", "angle": "Strong MPG and warranty in the compact class."},
        {"make": "Toyota", "model": "Prius", "angle": "Hybrid benchmark for fuel-conscious buyers."},
    ],
    "road_trip": [
        {"make": "Honda", "model": "Accord", "angle": "Comfortable highway cruiser with efficient powertrains."},
        {"make": "Toyota", "model": "Camry", "angle": "Reliable long-distance sedan with available hybrid MPG."},
        {"make": "Subaru", "model": "Outback", "angle": "AWD confidence and cargo space for gear."},
        {"make": "Mazda", "model": "CX-5", "angle": "Quiet cabin and upscale road manners."},
    ],
    "minivan": [
        {"make": "Toyota", "model": "Sienna", "angle": "Hybrid-first minivan with strong reliability and cargo flexibility."},
        {"make": "Honda", "model": "Odyssey", "angle": "Family minivan known for packaging, seats, and cargo space."},
        {"make": "Chrysler", "model": "Pacifica", "angle": "Spacious cabin with available hybrid and Stow 'n Go seating."},
        {"make": "Kia", "model": "Carnival", "angle": "SUV-styled minivan with a large cargo and passenger footprint."},
    ],
    "crossover": [
        {"make": "Honda", "model": "CR-V", "angle": "Practical compact crossover with strong resale and family-friendly packaging."},
        {"make": "Subaru", "model": "Forester", "angle": "Standard AWD crossover with upright visibility and outdoor utility."},
        {"make": "Toyota", "model": "RAV4", "angle": "Popular compact SUV with AWD options and proven ownership costs."},
        {"make": "Mazda", "model": "CX-5", "angle": "Upscale compact crossover with engaging driving manners."},
    ],
    "electric": [
        {"make": "Tesla", "model": "Model Y", "angle": "Popular electric crossover with strong range and software features."},
        {"make": "Ford", "model": "Mustang Mach-E", "angle": "Electric SUV with engaging drive modes and competitive range."},
        {"make": "Hyundai", "model": "Ioniq 5", "angle": "Stylish EV crossover with fast charging and spacious cabin."},
        {"make": "Volkswagen", "model": "ID.4", "angle": "Practical electric SUV with value-focused trims."},
    ],
}

BRAND_STORY_MODELS: dict[str, list[dict[str, str]]] = {
    "Toyota": [
        {"model": "Camry", "angle": "Reliability benchmark sedan with hybrid options."},
        {"model": "Tacoma", "angle": "Midsize truck known for durability and resale."},
        {"model": "RAV4", "angle": "Compact SUV with AWD and broad trim ladder."},
    ],
    "Ford": [
        {"model": "F-150", "angle": "America's best-selling truck with wide capability range."},
        {"model": "Explorer", "angle": "Three-row family SUV with truck-based heritage."},
        {"model": "Bronco", "angle": "Off-road focused SUV with removable doors."},
    ],
    "Honda": [
        {"model": "Civic", "angle": "Efficient compact with strong owner satisfaction."},
        {"model": "Accord", "angle": "Refined midsize sedan for daily and road-trip duty."},
        {"model": "CR-V", "angle": "Practical compact SUV with family-friendly packaging."},
    ],
    "Chevrolet": [
        {"model": "Silverado 1500", "angle": "Full-size truck with competitive towing."},
        {"model": "Equinox", "angle": "Value-oriented compact SUV."},
        {"model": "Traverse", "angle": "Spacious three-row for large households."},
    ],
    "Jeep": [
        {"model": "Wrangler", "angle": "Trail-first 4x4 with removable top."},
        {"model": "Grand Cherokee", "angle": "Premium SUV with available 4x4 hardware."},
    ],
    "Subaru": [
        {"model": "Outback", "angle": "AWD wagon built for outdoor lifestyles."},
        {"model": "Forester", "angle": "Practical AWD SUV with upright visibility."},
    ],
}

BODY_TYPE_MODELS: dict[str, list[dict[str, Any]]] = {
    "Pickup": [
        {"make": "Ford", "model": "F-150", "sample_year": 2019, "note": "Best-selling full-size truck with broad trim ladder."},
        {"make": "Ford", "model": "F-150", "sample_year": 2019, "trim": "Raptor", "note": "High-performance off-road trim; often above mainstream budgets."},
        {"make": "Toyota", "model": "Tacoma", "sample_year": 2020, "note": "Known for reliability and strong resale in the midsize segment."},
        {"make": "Toyota", "model": "Tundra", "sample_year": 2019, "note": "Full-size Toyota truck with strong reliability and 4x4 options."},
        {"make": "Chevrolet", "model": "Silverado 1500", "sample_year": 2019, "note": "Full-size workhorse with competitive towing."},
        {"make": "Ram", "model": "1500", "sample_year": 2020, "note": "Comfort-oriented full-size truck with upscale interior options."},
    ],
    "SUV": [
        {"make": "Toyota", "model": "RAV4", "sample_year": 2020, "note": "Popular compact SUV with AWD options and strong resale."},
        {"make": "Honda", "model": "CR-V", "sample_year": 2020, "note": "Practical crossover with family-friendly packaging."},
        {"make": "Subaru", "model": "Forester", "sample_year": 2020, "note": "Standard AWD crossover with upright visibility."},
        {"make": "Mazda", "model": "CX-5", "sample_year": 2020, "note": "Upscale compact crossover with refined road manners."},
    ],
    "Minivan": [
        {"make": "Toyota", "model": "Sienna", "sample_year": 2022, "note": "Hybrid minivan with strong reliability and flexible cargo space."},
        {"make": "Honda", "model": "Odyssey", "sample_year": 2022, "note": "Family favorite with clever seating and large cargo capacity."},
        {"make": "Chrysler", "model": "Pacifica", "sample_year": 2022, "note": "Spacious cabin with available hybrid and Stow 'n Go seats."},
        {"make": "Kia", "model": "Carnival", "sample_year": 2022, "note": "SUV-styled minivan with a roomy passenger and cargo footprint."},
    ],
    "Van": [
        {"make": "Toyota", "model": "Sienna", "sample_year": 2022, "note": "Hybrid minivan with strong reliability and flexible cargo space."},
        {"make": "Honda", "model": "Odyssey", "sample_year": 2022, "note": "Family favorite with clever seating and large cargo capacity."},
        {"make": "Chrysler", "model": "Pacifica", "sample_year": 2022, "note": "Spacious cabin with available hybrid and Stow 'n Go seats."},
        {"make": "Kia", "model": "Carnival", "sample_year": 2022, "note": "SUV-styled minivan with a roomy passenger and cargo footprint."},
    ],
}


def _research_year(criteria: dict[str, Any], candidate: Optional[dict[str, Any]] = None) -> int:
    """Year used for recalls/listings when the user has not picked one yet."""
    if criteria.get("year"):
        return int(criteria["year"])
    if criteria.get("year_max"):
        return int(criteria["year_max"])
    if criteria.get("year_min"):
        return int(criteria["year_min"])
    if candidate and candidate.get("sample_year"):
        return int(candidate["sample_year"])
    return datetime.now().year - 4


def _display_year(criteria: dict[str, Any], candidate: dict[str, Any]) -> Optional[int]:
    """Only show a year on cards when the user or catalog explicitly provides one."""
    if criteria.get("year"):
        return int(criteria["year"])
    if criteria.get("year_max"):
        return int(criteria["year_max"])
    if candidate.get("sample_year"):
        return int(candidate["sample_year"])
    return None


def _detect_use_cases(message: str, criteria: Optional[dict[str, Any]] = None) -> list[str]:
    text = message.lower()
    criteria = criteria or {}
    use_case_text = str(criteria.get("use_case") or "").lower()
    body_text = str(criteria.get("body_type") or "").lower()
    combined = f"{text} {use_case_text} {body_text}"
    cases = []
    if any(word in combined for word in ["outdoor", "camping", "hiking", "off-road", "off road", "trail"]):
        cases.append("outdoors")
    if any(
        word in combined
        for word in ["family", "kids", "three row", "3-row", "large family", "seating"]
    ):
        cases.append("large_family")
    if any(
        word in combined
        for word in ["mpg", "gas mileage", "fuel economy", "good on gas", "hybrid", "efficient"]
    ):
        cases.append("fuel_economy")
    if any(word in combined for word in ["road trip", "roadtrip", "highway", "commute", "travel"]):
        cases.append("road_trip")
    if any(
        word in combined
        for word in ["minivan", "mini van", "mini-van", "cargo van", "sienna", "odyssey", "pacifica", "carnival"]
    ) or ("cargo" in combined and "van" in combined):
        cases.append("minivan")
    if (
        any(
            word in combined
            for word in [
                "electric",
                "battery electric",
                "zero emission",
                "plug-in",
                "ioniq",
                "mach-e",
                "mach e",
                "id.4",
                "id4",
            ]
        )
        or re.search(r"\bev\b", combined)
        or ("electric" in combined and "suv" in combined)
    ):
        cases.append("electric")
    elif any(
        word in combined
        for word in [
            "crossover",
            "cuv",
            "compact suv",
            "compact crossover",
            "awd crossover",
            "4wd crossover",
        ]
    ) or (
        any(word in combined for word in ["awd", "4wd", "all wheel", "4x4"])
        and any(word in combined for word in ["suv", "crossover", "cuv"])
    ):
        cases.append("crossover")
    return cases


def _detect_brand(message: str, criteria: dict[str, Any]) -> Optional[str]:
    if criteria.get("make"):
        return str(criteria["make"])
    text = message.lower()
    for brand in BRAND_STORY_MODELS:
        if brand.lower() in text:
            return brand
    return None


def _pick_candidate_models(criteria: dict[str, Any], message: str) -> list[dict[str, Any]]:
    if criteria.get("make") and criteria.get("model"):
        year = _research_year(criteria)
        return [{"make": criteria["make"], "model": criteria["model"], "sample_year": year}]

    picks: list[dict[str, Any]] = []
    brand = _detect_brand(message, criteria)
    if brand and not criteria.get("model"):
        for item in BRAND_STORY_MODELS.get(brand, []):
            picks.append({"make": brand, **item})

    # Use both the latest message and saved criteria so follow-up turns
    # like "nothing appeared" still keep the prior minivan/SUV context.
    for case in _detect_use_cases(message, criteria):
        picks.extend(USE_CASE_MODELS.get(case, []))

    body = str(criteria.get("body_type") or "").strip()
    if body and body in BODY_TYPE_MODELS:
        picks.extend(BODY_TYPE_MODELS[body])
    elif body.lower() in {"minivan", "mini van", "van"}:
        picks.extend(BODY_TYPE_MODELS["Minivan"])
    elif body.lower() in {"crossover", "cuv", "compact suv", "suv"}:
        picks.extend(BODY_TYPE_MODELS["SUV"])

    if not picks and body == "Pickup":
        picks.extend(BODY_TYPE_MODELS["Pickup"])

    deduped = []
    seen = set()
    for item in picks:
        key = (item["make"], item["model"], item.get("trim", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:4]


def _pick_recall_years(criteria: dict[str, Any], message: str) -> list[int]:
    years: list[int] = []

    for key in ("year", "year_max", "year_min"):
        value = criteria.get(key)
        if value:
            years.append(int(value))

    for match in re.findall(r"\b(20\d{2})\b", message):
        years.append(int(match))

    if not years:
        reference = datetime.now().year - 3
        years = [reference, reference - 2, reference - 4, reference - 6]

    unique: list[int] = []
    seen: set[int] = set()
    current_year = datetime.now().year
    for year in sorted(years, reverse=True):
        if year in seen or year < 1990 or year > current_year + 1:
            continue
        seen.add(year)
        unique.append(year)
        if len(unique) >= MAX_RECALL_YEARS:
            break
    return unique


def _recall_row_for_year(make: str, model: str, year: int) -> Optional[dict[str, Any]]:
    is_valid, _, canonical_make, canonical = verify_vehicle_exists(make, year, model)
    if not is_valid:
        return None

    recalls = get_live_recalls(canonical_make, year, canonical, verbose=False)
    if recalls.get("available") is False or recalls.get("error"):
        return {
            "year": year,
            "recall_count": None,
            "recalls_available": False,
            "recalls": [],
        }
    return {
        "year": year,
        "recall_count": recalls.get("total_recalls_count", 0),
        "recalls_available": True,
        "recalls": recalls.get("recalls_list", [])[:3],
    }


def _recalls_for_years(
    make: str,
    model: str,
    criteria: dict[str, Any],
    message: str,
) -> list[dict[str, Any]]:
    years = _pick_recall_years(criteria, message)
    if not years:
        return []

    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=RECALL_FETCH_WORKERS) as pool:
        futures = {
            pool.submit(_recall_row_for_year, make, model, year): year for year in years
        }
        try:
            for future in as_completed(futures, timeout=RECALL_FETCH_TIMEOUT):
                try:
                    row = future.result()
                    if row:
                        rows.append(row)
                except Exception:
                    continue
        except TimeoutError:
            for future in futures:
                future.cancel()

    rows.sort(key=lambda row: row["year"], reverse=True)
    return rows


def _sample_listing(make: str, model: str, year: int, zip_code: Optional[str]) -> dict[str, Any]:
    allow_nationwide = (
        os.environ.get("ASSISTANT_MARKET_LOOKUPS_WITHOUT_ZIP", "false").strip().lower()
        in {"1", "true", "yes"}
    )
    if not zip_code and not allow_nationwide:
        return {}

    criteria = {"make": make, "model": model, "year": year}
    if zip_code:
        criteria["zip_code"] = zip_code
    try:
        snapshot = search_by_criteria(criteria, rows=1, enrich_prices=False)
        if snapshot["listings"]:
            listing = snapshot["listings"][0]
            return {
                "heading": listing.get("heading"),
                "price": listing.get("price"),
                "miles": listing.get("miles"),
                "photo": listing.get("primary_photo"),
                "fuel_type": listing.get("fuel_type"),
            }
    except MarketCheckError:
        pass
    return {}


def _criteria_with_message_focus(
    criteria: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    if criteria.get("make") and criteria.get("model"):
        return criteria

    match = re.search(
        r"\b(20\d{2})\s+([A-Za-z][A-Za-z-]*)\s+([A-Za-z0-9][\w-]*)",
        message,
    )
    if not match:
        return criteria

    year, make, model = match.groups()
    merged = dict(criteria)
    merged.setdefault("make", make)
    merged.setdefault("model", model)
    merged.setdefault("year", int(year))
    return merged


def build_research_bundle(criteria: dict[str, Any], message: str) -> dict[str, Any]:
    criteria = _criteria_with_message_focus(criteria, message)
    zip_code = criteria.get("zip_code")
    candidates = _pick_candidate_models(criteria, message)
    bundle: dict[str, Any] = {
        "use_cases_detected": _detect_use_cases(message, criteria),
        "candidate_models": [],
        "model_deep_dive": None,
    }

    if criteria.get("make") and criteria.get("model"):
        make = criteria["make"]
        model = criteria["model"]
        recall_rows = _recalls_for_years(make, model, criteria, message)
        available_rows = [
            row for row in recall_rows if isinstance(row.get("recall_count"), int)
        ]
        high_recall = sorted(
            available_rows, key=lambda row: row["recall_count"], reverse=True
        )[:3]
        sample_year = _research_year(criteria)
        bundle["model_deep_dive"] = {
            "make": make,
            "model": model,
            "competitors": get_competitors(make, model).get("people_also_shop", []),
            "recalls_by_year": recall_rows,
            "years_to_consider": [
                row["year"]
                for row in sorted(available_rows, key=lambda r: r["recall_count"])[:3]
            ],
            "years_to_scrutinize": [
                row["year"] for row in high_recall if row["recall_count"] >= 3
            ],
            "sample_listing": _sample_listing(make, model, sample_year, zip_code),
        }
        return bundle

    for candidate in candidates:
        sample_year = _research_year(criteria, candidate)
        display_year = _display_year(criteria, candidate)
        is_valid, _, canonical_make, canonical = verify_vehicle_exists(
            candidate["make"], sample_year, candidate["model"]
        )
        if not is_valid:
            continue

        recalls = get_live_recalls(canonical_make, sample_year, canonical, verbose=False)
        listing = _sample_listing(canonical_make, canonical, sample_year, zip_code)
        recall_ok = not (recalls.get("available") is False or recalls.get("error"))
        bundle["candidate_models"].append(
            {
                "make": canonical_make,
                "model": canonical,
                "trim": candidate.get("trim"),
                "sample_year": sample_year,
                "display_year": display_year,
                "positioning_note": candidate.get("note") or candidate.get("angle"),
                "recall_count": recalls.get("total_recalls_count") if recall_ok else None,
                "recalls_available": recall_ok,
                "top_recalls": recalls.get("recalls_list", [])[:2] if recall_ok else [],
                "sample_listing": listing,
            }
        )

    return bundle


def build_highlights(bundle: dict[str, Any], criteria: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    highlights = []
    criteria = criteria or {}

    if bundle.get("model_deep_dive"):
        dive = bundle["model_deep_dive"]
        listing = dive.get("sample_listing") or {}
        display_year = criteria.get("year") or criteria.get("year_max")
        year_value = int(display_year) if display_year else None
        photo_meta = resolve_vehicle_photo(
            listing.get("photo"),
            dive["make"],
            dive["model"],
            year_value,
        )
        highlights.append(
            {
                "id": f"{dive['make']}-{dive['model']}-focus",
                "make": dive["make"],
                "model": dive["model"],
                "year": year_value,
                "title": f"{dive['make']} {dive['model']}",
                "photo": photo_meta.get("photo"),
                "photo_source": photo_meta.get("photo_source"),
                "summary": "Focused model research with year guidance and recall context.",
            }
        )
        return highlights

    for item in bundle.get("candidate_models", []):
        listing = item.get("sample_listing") or {}
        trim = item.get("trim") or ""
        sample_year = item.get("sample_year")
        display_year = item.get("display_year")
        year_for_image = display_year or sample_year
        photo_meta = resolve_vehicle_photo(
            listing.get("photo"),
            item["make"],
            item["model"],
            int(year_for_image) if year_for_image else None,
        )
        highlight_id = "-".join(
            part
            for part in [
                item["make"],
                item["model"],
                str(display_year) if display_year else "na",
                trim or "base",
            ]
            if part
        )
        highlights.append(
            {
                "id": highlight_id,
                "make": item["make"],
                "model": item["model"],
                "trim": trim or None,
                "year": display_year,
                "title": f"{item['make']} {item['model']}" + (f" {trim}" if trim else ""),
                "photo": photo_meta.get("photo"),
                "photo_source": photo_meta.get("photo_source"),
                "summary": item.get("positioning_note", ""),
            }
        )
    return highlights


MAKE_ALIASES = {
    "chevy": "chevrolet",
    "chevrolet": "chevy",
}


def _mentioned_in_text(make: str, model: str, text: str) -> bool:
    text_lower = text.lower()
    make_lower = make.lower()
    model_lower = model.lower()

    if make_lower in text_lower and model_lower in text_lower:
        return True

    for alias, partner in MAKE_ALIASES.items():
        if make_lower in {alias, partner}:
            other = partner if make_lower == alias else alias
            if other in text_lower and model_lower in text_lower:
                return True

    return False


def _competitor_pool(bundle: dict[str, Any]) -> list[dict[str, str]]:
    pool: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(make: str, model: str) -> None:
        key = (make.lower(), model.lower())
        if key in seen:
            return
        seen.add(key)
        pool.append({"make": make, "model": model})

    if bundle.get("model_deep_dive"):
        dive = bundle["model_deep_dive"]
        for item in get_competitors(dive["make"], dive["model"])["competitors"]:
            add(item["make"], item["model"])

    for item in bundle.get("candidate_models", []):
        add(item["make"], item["model"])
        for comp in get_competitors(item["make"], item["model"])["competitors"]:
            add(comp["make"], comp["model"])

    return pool


def _competitor_summary(
    make: str,
    model: str,
    bundle: dict[str, Any],
    recall_count: Optional[int],
) -> str:
    dive = bundle.get("model_deep_dive") or {}
    focus_make = dive.get("make")
    focus_model = dive.get("model")
    if recall_count is None:
        recall_phrase = "Recall data unavailable for the sample year."
    else:
        recall_phrase = f"{recall_count} active recalls on the sample year."
    if focus_make and focus_model:
        return (
            f"Cross-shopped rival to the {focus_make} {focus_model}. "
            f"{recall_phrase}"
        )
    return f"Popular alternative in this segment. {recall_phrase}"


def build_competitor_highlights(
    bundle: dict[str, Any],
    criteria: dict[str, Any],
    assistant_message: str,
    primary_highlights: Optional[list[dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    if not assistant_message.strip():
        return []

    primary_keys = {
        (item["make"].lower(), item["model"].lower())
        for item in (primary_highlights or [])
    }

    highlights: list[dict[str, Any]] = []
    zip_code = criteria.get("zip_code")

    for candidate in _competitor_pool(bundle):
        make = candidate["make"]
        model = candidate["model"]
        key = (make.lower(), model.lower())

        if key in primary_keys:
            continue
        if not _mentioned_in_text(make, model, assistant_message):
            continue

        sample_year = _research_year(criteria, candidate)
        display_year = _display_year(criteria, candidate)
        is_valid, _, canonical_make, canonical = verify_vehicle_exists(make, sample_year, model)
        if not is_valid:
            continue

        recalls = get_live_recalls(canonical_make, sample_year, canonical, verbose=False)
        listing = _sample_listing(canonical_make, canonical, sample_year, zip_code)
        recall_ok = not (recalls.get("available") is False or recalls.get("error"))
        recall_count = recalls.get("total_recalls_count", 0) if recall_ok else None
        make = canonical_make
        photo_meta = resolve_vehicle_photo(
            listing.get("photo"),
            make,
            canonical,
            int(display_year or sample_year) if (display_year or sample_year) else None,
        )

        highlights.append(
            {
                "id": f"competitor-{make}-{canonical}-{display_year or sample_year}",
                "make": make,
                "model": canonical,
                "year": display_year,
                "title": f"{make} {canonical}",
                "photo": photo_meta.get("photo"),
                "photo_source": photo_meta.get("photo_source"),
                "summary": _competitor_summary(make, canonical, bundle, recall_count),
                "kind": "competitor",
            }
        )

    return highlights[:4]


# Real trim ladders used for follow-up chips (avoid generic Base/Mid/Top).
MODEL_TRIM_OPTIONS: dict[tuple[str, str], list[str]] = {
    ("Toyota", "Prius"): ["LE", "XLE", "Limited"],
    ("Toyota", "Camry"): ["LE", "SE", "XLE", "XSE"],
    ("Toyota", "Corolla"): ["LE", "SE", "XLE"],
    ("Toyota", "RAV4"): ["LE", "XLE", "XLE Premium", "Limited"],
    ("Toyota", "Tacoma"): ["SR", "SR5", "TRD Off-Road", "TRD Pro"],
    ("Toyota", "Tundra"): ["SR5", "Limited", "1794 Edition", "TRD Pro"],
    ("Honda", "Civic"): ["LX", "Sport", "EX", "Touring"],
    ("Honda", "Accord"): ["LX", "EX-L", "Sport", "Touring"],
    ("Honda", "CR-V"): ["LX", "EX", "EX-L", "Touring"],
    ("Honda", "Pilot"): ["Sport", "EX-L", "TrailSport", "Touring"],
    ("Subaru", "Forester"): ["Premium", "Sport", "Limited", "Touring"],
    ("Subaru", "Outback"): ["Premium", "Onyx Edition", "Limited", "Touring"],
    ("Mazda", "CX-5"): ["2.5 S", "Preferred", "Carbon Edition", "Premium Plus"],
    ("Ford", "F-150"): ["XL", "XLT", "Lariat", "Raptor"],
    ("Ram", "1500"): ["Tradesman", "Big Horn", "Laramie", "TRX"],
    ("Chevrolet", "Silverado 1500"): ["WT", "LT", "RST", "LTZ"],
    ("Kia", "Telluride"): ["LX", "S", "EX", "SX"],
    ("Hyundai", "Ioniq 5"): ["SE", "SEL", "Limited"],
    ("Ford", "Mustang Mach-E"): ["Select", "Premium", "GT"],
    ("Volkswagen", "ID.4"): ["Standard", "Pro", "Pro S"],
    ("GMC", "Hummer EV SUV"): ["2X", "3X", "Omega"],
    ("GMC", "Hummer EV Pickup"): ["2X", "3X", "Omega"],
}

# If only one value, we auto-apply it and skip the drivetrain question.
MODEL_DRIVETRAIN_OPTIONS: dict[tuple[str, str], list[str]] = {
    ("Toyota", "Prius"): ["FWD"],
    ("Toyota", "Camry"): ["FWD"],
    ("Toyota", "Corolla"): ["FWD"],
    ("Toyota", "Prius Prime"): ["FWD"],
    ("Honda", "Civic"): ["FWD"],
    ("Honda", "Accord"): ["FWD"],
    ("Toyota", "RAV4"): ["FWD", "AWD"],
    ("Honda", "CR-V"): ["FWD", "AWD"],
    ("Honda", "Pilot"): ["FWD", "AWD"],
    ("Mazda", "CX-5"): ["FWD", "AWD"],
    ("Subaru", "Forester"): ["AWD"],
    ("Subaru", "Outback"): ["AWD"],
    ("Ford", "F-150"): ["RWD", "4WD"],
    ("Ram", "1500"): ["RWD", "4WD"],
    ("Chevrolet", "Silverado 1500"): ["RWD", "4WD"],
    ("Toyota", "Tacoma"): ["RWD", "4WD"],
    ("Toyota", "Tundra"): ["RWD", "4WD"],
    ("Kia", "Telluride"): ["FWD", "AWD"],
    ("Hyundai", "Ioniq 5"): ["RWD", "AWD"],
    ("Ford", "Mustang Mach-E"): ["RWD", "AWD"],
    ("Volkswagen", "ID.4"): ["RWD", "AWD"],
    ("GMC", "Hummer EV SUV"): ["AWD"],
    ("GMC", "Hummer EV Pickup"): ["AWD"],
}

MODEL_FOLLOW_UP_HINTS: dict[tuple[str, str], list[dict[str, str]]] = {
    ("Ram", "1500"): [
        {"label": "TRX", "message": "I'm interested in the Ram 1500 TRX trim"},
        {"label": "5.7L Hemi", "message": "Tell me about the Ram 1500 with the 5.7L Hemi engine"},
        {"label": "Laramie", "message": "I'm interested in the Ram 1500 Laramie trim"},
    ],
    ("Ford", "F-150"): [
        {"label": "XLT", "message": "I'm interested in the Ford F-150 XLT trim"},
        {"label": "Lariat", "message": "I'm interested in the Ford F-150 Lariat trim"},
        {"label": "Raptor", "message": "I'm interested in the Ford F-150 Raptor trim"},
    ],
    ("Toyota", "Tacoma"): [
        {"label": "TRD Off-Road", "message": "I'm interested in the Toyota Tacoma TRD Off-Road trim"},
        {"label": "TRD Pro", "message": "I'm interested in the Toyota Tacoma TRD Pro trim"},
    ],
    ("Chevrolet", "Silverado 1500"): [
        {"label": "LT", "message": "I'm interested in the Silverado 1500 LT trim"},
        {"label": "Z71", "message": "I'm interested in the Silverado 1500 Z71 package"},
        {"label": "5.3L V8", "message": "Tell me about the Silverado 1500 with the 5.3L V8"},
    ],
    ("Toyota", "Tundra"): [
        {"label": "TRD Pro", "message": "I'm interested in the Toyota Tundra TRD Pro trim"},
        {"label": "1794 Edition", "message": "I'm interested in the Tundra 1794 Edition trim"},
    ],
    ("Toyota", "Prius"): [
        {"label": "LE", "message": "I'm interested in the Toyota Prius LE trim"},
        {"label": "XLE", "message": "I'm interested in the Toyota Prius XLE trim"},
        {"label": "Limited", "message": "I'm interested in the Toyota Prius Limited trim"},
    ],
    ("GMC", "Hummer EV SUV"): [
        {"label": "2X", "message": "I'm interested in the GMC Hummer EV SUV 2X trim"},
        {"label": "3X", "message": "I'm interested in the GMC Hummer EV SUV 3X trim"},
        {"label": "Omega", "message": "I'm interested in the GMC Hummer EV SUV Omega edition"},
    ],
    ("GMC", "Hummer EV Pickup"): [
        {"label": "2X", "message": "I'm interested in the GMC Hummer EV Pickup 2X trim"},
        {"label": "3X", "message": "I'm interested in the GMC Hummer EV Pickup 3X trim"},
        {"label": "Omega", "message": "I'm interested in the GMC Hummer EV Pickup Omega edition"},
    ],
}


_DRIVETRAIN_LABELS = {"4wd", "awd", "fwd", "rwd", "4x4"}


def model_trim_options(make: Optional[str], model: Optional[str]) -> list[str]:
    if not make or not model:
        return []
    return list(MODEL_TRIM_OPTIONS.get((str(make).strip(), str(model).strip()), []))


def model_drivetrain_options(make: Optional[str], model: Optional[str]) -> list[str]:
    if not make or not model:
        return []
    return list(MODEL_DRIVETRAIN_OPTIONS.get((str(make).strip(), str(model).strip()), []))


def _normalize_make_model_key(make: str, model: str) -> tuple[str, str]:
    return make.strip(), model.strip()


_BODY_TYPE_CHIP_LABELS = {
    "sedan",
    "suv",
    "crossover",
    "truck",
    "pickup",
    "minivan",
    "van",
    "coupe",
    "hatchback",
    "wagon",
}


def _option_labels_are_years(options: list[dict[str, str]]) -> bool:
    if not options:
        return False
    return all(str(option.get("label", "")).strip().isdigit() for option in options)


def _follow_up_prompt(
    criteria: dict[str, Any],
    narrowing: dict[str, Any],
    options: list[dict[str, str]],
    response_mode: str,
) -> str:
    make = criteria.get("make")
    model = criteria.get("model")
    vehicle = f"{make} {model}".strip() if make and model else ""
    suggested = narrowing.get("suggested_next_question")

    if suggested == "ask_year_range":
        return (
            f"Which years are you looking for in the {vehicle}?"
            if vehicle
            else "Which years are you looking for?"
        )
    if suggested == "ask_trim":
        return (
            f"Which {vehicle} trim or engine option interests you?"
            if vehicle
            else "Which trim or engine option interests you?"
        )
    if suggested == "ask_drivetrain":
        return (
            f"Which drivetrain do you want for the {vehicle}?"
            if vehicle
            else "Which drivetrain do you prefer?"
        )
    if suggested == "ask_max_mileage":
        return "What's the maximum mileage you're comfortable with?"
    if suggested == "ask_trim_or_mileage":
        return (
            f"Which {vehicle} trim or mileage range works for you?"
            if vehicle != "this vehicle"
            else "Which trim or mileage range works for you?"
        )
    if suggested == "ask_budget":
        return "Before I load live cars, which $5,000 price range works for you? I’ll ask for your ZIP next."
    if suggested == "ask_model_preference":
        return "Which model interests you most?"
    if suggested == "ask_zip_code":
        return "What's your ZIP code for nearby listings?"
    if suggested == "ask_features_or_confirm_search" and vehicle:
        return f"What details matter most for the {vehicle}?"

    # Only claim "years" when every chip is a year — mixed Sedan/2022 chips used to
    # trigger a year prompt incorrectly.
    if _option_labels_are_years(options):
        return (
            f"Which years are you looking for in the {vehicle}?"
            if vehicle
            else "Which years are you looking for?"
        )

    if response_mode == "discover":
        return "Which model would you like to explore?"

    return "What would you like to explore next?"


def _sanitize_ai_follow_up_options(
    suggested: str,
    ai_options: Optional[list[dict[str, Any]]],
) -> list[dict[str, str]]:
    """Keep only chips that match the current narrowing question."""
    cleaned: list[dict[str, str]] = []
    seen: set[str] = set()
    for opt in ai_options or []:
        label = str(opt.get("label", "")).strip()
        message = str(opt.get("message") or label).strip()
        if not label or not message:
            continue
        key = label.lower()
        if key in seen:
            continue
        is_year = label.isdigit()
        is_body = key in _BODY_TYPE_CHIP_LABELS
        if suggested == "ask_year_range" and not is_year:
            continue
        if suggested == "ask_model_preference" and (is_year or is_body):
            continue
        if suggested == "ask_budget" and "$" not in label and "k" not in key:
            continue
        if suggested in {"ask_max_mileage", "ask_trim_or_mileage"} and is_year:
            continue
        if suggested == "ask_drivetrain" and key not in {"4wd", "awd", "fwd", "rwd", "4x4"}:
            continue
        seen.add(key)
        cleaned.append({"label": label, "message": message})
    return cleaned


NARROWING_OPTION_BUILDERS = {
    "ask_budget",
    "ask_year_range",
    "ask_trim",
    "ask_trim_or_mileage",
    "ask_drivetrain",
    "ask_max_mileage",
    "ask_zip_code",
    "ask_model_preference",
    "ask_features_or_confirm_search",
}


def _vehicle_label(criteria: dict[str, Any]) -> str:
    make = criteria.get("make")
    model = criteria.get("model")
    if make and model:
        return f"{make} {model}"
    return "this vehicle"


def _build_narrowing_options(
    suggested: str,
    criteria: dict[str, Any],
    research_bundle: dict[str, Any],
    highlights: Optional[list[dict[str, Any]]],
    response_mode: str,
) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(label: str, message: str) -> None:
        clean_label = label.strip()
        clean_message = message.strip()
        if not clean_label or not clean_message:
            return
        key = clean_label.lower()
        if key in seen:
            return
        seen.add(key)
        options.append({"label": clean_label, "message": clean_message})

    make = criteria.get("make")
    model = criteria.get("model")
    vehicle = _vehicle_label(criteria)
    dive = research_bundle.get("model_deep_dive")
    hint_key = _normalize_make_model_key(str(make), str(model)) if make and model else None
    hints = MODEL_FOLLOW_UP_HINTS.get(hint_key, []) if hint_key else []

    if suggested == "ask_budget":
        for minimum in (15000, 20000, 25000, 30000, 35000, 40000):
            maximum = minimum + 5000
            add(
                f"${minimum // 1000}k–${maximum // 1000}k",
                f"My price range is ${minimum:,} to ${maximum:,} for the {vehicle}",
            )
        return options[:6]

    if suggested == "ask_year_range":
        if dive:
            for year in dive.get("years_to_consider", [])[:5]:
                add(str(year), f"I'm interested in the {year} {make} {model}")
        for hint in hints:
            if hint["label"].isdigit():
                add(hint["label"], hint["message"])
        if not options:
            reference = datetime.now().year - 3
            for year in range(reference, reference - 5, -1):
                add(str(year), f"I'm interested in the {year} {vehicle}")
        return options[:6]

    if suggested == "ask_trim":
        for trim in model_trim_options(make, model):
            add(trim, f"I'm interested in the {vehicle} {trim} trim")
        for hint in hints:
            label = str(hint.get("label", "")).strip()
            if not label or label.isdigit() or label.lower() in _DRIVETRAIN_LABELS:
                continue
            add(label, hint["message"])
        # Never fall back to vague Base/Mid/Top — those cause loops and bad trim capture.
        if not options and make and model:
            add("Common trims", f"What trims are most common for the {vehicle}?")
        return options[:6]

    if suggested == "ask_trim_or_mileage":
        for trim in model_trim_options(make, model)[:3]:
            add(trim, f"I'm interested in the {vehicle} {trim} trim")
        for hint in hints:
            label = str(hint.get("label", "")).strip()
            if not label or label.isdigit() or label.lower() in _DRIVETRAIN_LABELS:
                continue
            add(label, hint["message"])
        for label, miles in (
            ("Under 75k", 75000),
            ("Under 100k", 100000),
            ("Under 150k", 150000),
        ):
            add(label, f"I want {vehicle} listings under {miles:,} miles")
        return options[:6]

    if suggested == "ask_drivetrain":
        available = model_drivetrain_options(make, model) or ["4WD", "AWD", "FWD", "RWD"]
        for drivetrain in available:
            add(drivetrain, f"I want a {drivetrain} {vehicle}")
        return options[:6]

    if suggested == "ask_max_mileage":
        for label, miles in (
            ("Under 50k", 50000),
            ("Under 75k", 75000),
            ("Under 100k", 100000),
            ("Under 150k", 150000),
        ):
            add(label, f"I want {vehicle} listings under {miles:,} miles")
        add("Any mileage", "Mileage is not a major concern for me")
        return options[:6]

    if suggested == "ask_zip_code":
        add("Enter ZIP in chat", "I want to search listings near my ZIP code")
        return options[:6]

    if suggested == "ask_model_preference":
        for item in highlights or []:
            add(
                f"{item['make']} {item['model']}",
                f"I'm interested in the {item['make']} {item['model']}",
            )
        if not options:
            for item in research_bundle.get("candidate_models") or []:
                add(
                    f"{item['make']} {item['model']}",
                    f"I'm interested in the {item['make']} {item['model']}",
                )
        return options[:6]

    if suggested == "ask_features_or_confirm_search" and make and model:
        if dive:
            for year in dive.get("years_to_consider", [])[:3]:
                add(str(year), f"I'm interested in the {year} {make} {model}")
        for hint in hints[:3]:
            add(hint["label"], hint["message"])
        add(
            "Explore other options",
            f"Show me other options besides the {make} {model}",
        )
        return options[:6]

    return []


def build_follow_up_options(
    criteria: dict[str, Any],
    research_bundle: dict[str, Any],
    narrowing: dict[str, Any],
    ai_options: Optional[list[dict[str, Any]]] = None,
    highlights: Optional[list[dict[str, Any]]] = None,
    response_mode: str = "discover",
) -> dict[str, Any]:
    suggested = narrowing.get("suggested_next_question", "")

    if suggested in NARROWING_OPTION_BUILDERS:
        options = _build_narrowing_options(
            suggested,
            criteria,
            research_bundle,
            highlights,
            response_mode,
        )
        if options:
            return {
                "options": options[:6],
                "prompt": _follow_up_prompt(criteria, narrowing, options, response_mode),
            }

    options: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(label: str, message: str) -> None:
        clean_label = label.strip()
        clean_message = message.strip()
        if not clean_label or not clean_message:
            return
        key = clean_label.lower()
        if key in seen:
            return
        seen.add(key)
        options.append({"label": clean_label, "message": clean_message})

    # Only keep AI chips that match the current question — never mix Sedan + years.
    for opt in _sanitize_ai_follow_up_options(suggested, ai_options):
        add(opt["label"], opt["message"])

    make = criteria.get("make")
    model = criteria.get("model")
    dive = research_bundle.get("model_deep_dive")

    if make and model and response_mode == "model_focus":
        if dive:
            for year in dive.get("years_to_consider", [])[:3]:
                add(str(year), f"I'm interested in the {year} {make} {model}")
        if not options:
            key = _normalize_make_model_key(str(make), str(model))
            for hint in MODEL_FOLLOW_UP_HINTS.get(key, []):
                add(hint["label"], hint["message"])
        if not options:
            reference = datetime.now().year - 3
            for year in range(reference, reference - 4, -1):
                add(str(year), f"I'm interested in the {year} {make} {model}")

    elif make and model and response_mode == "option_focus":
        # Keep chips on the next narrowing step; avoid re-offering the broad overview.
        pass

    elif response_mode == "discover":
        # Prefer model chips only — ignore leftover AI body-type/year noise.
        options = []
        seen.clear()
        for item in highlights or []:
            add(
                f"{item['make']} {item['model']}",
                f"I'm interested in the {item['make']} {item['model']}",
            )

    final_options = options[:6]
    return {
        "options": final_options,
        "prompt": _follow_up_prompt(criteria, narrowing, final_options, response_mode),
    }
