import json
import re
from typing import Any, Optional

from app_ai_core import verify_vehicle_exists
from assistant_research import (
    build_competitor_highlights,
    build_follow_up_options,
    build_highlights,
    build_research_bundle,
    model_drivetrain_options,
    model_trim_options,
)
from openai_client import create_openai_client

client = create_openai_client()

PROFILE_FIELDS = [
    "make",
    "model",
    "year",
    "year_min",
    "year_max",
    "zip_code",
    "body_type",
    "drivetrain",
    "doors",
    "fuel_type",
    "min_mpg",
    "max_mpg",
    "max_price",
    "min_price",
    "max_miles",
    "trim",
    "notes",
    "use_case",
]

EMPTY_CRITERIA: dict[str, Any] = {field: None for field in PROFILE_FIELDS}

MIN_USER_TURNS_BEFORE_ZIP = 4


def _format_profile_text(criteria: dict[str, Any]) -> str:
    lines = ["=== YOUR VEHICLE SEARCH PROFILE ===", ""]
    populated = False

    labels = {
        "make": "Make",
        "model": "Model",
        "year": "Year",
        "year_min": "Year (min)",
        "year_max": "Year (max)",
        "zip_code": "ZIP code",
        "body_type": "Body style",
        "drivetrain": "Drivetrain",
        "doors": "Doors",
        "fuel_type": "Fuel type",
        "min_mpg": "Min MPG",
        "max_mpg": "Max MPG",
        "max_price": "Max budget",
        "min_price": "Min budget",
        "max_miles": "Max mileage",
        "trim": "Trim",
        "use_case": "Use case",
        "notes": "Notes",
    }

    for key, label in labels.items():
        value = criteria.get(key)
        if value not in (None, "", []):
            populated = True
            if key in {"max_price", "min_price"} and isinstance(value, (int, float)):
                lines.append(f"{label}: ${value:,.0f}")
            elif key == "max_miles" and isinstance(value, (int, float)):
                lines.append(f"{label}: {value:,.0f} miles")
            else:
                lines.append(f"{label}: {value}")

    if not populated:
        lines.append("No preferences captured yet.")
        lines.append("")
        lines.append('Try: "I want a 4x4 truck under $35,000"')
        lines.append('Or: "Good cars for road trips with great gas mileage"')
    else:
        lines.append("")
        lines.append("Carvest is building recommendations from your goals.")

    return "\n".join(lines)


def _count_user_turns(chat_history: list[dict[str, str]]) -> int:
    return sum(1 for item in chat_history if item.get("role") == "user")


def _missing_for_search(
    criteria: dict[str, Any],
    *,
    require_zip: bool = True,
) -> list[str]:
    missing = []

    if require_zip and not criteria.get("zip_code"):
        missing.append("zip_code")

    if not criteria.get("max_price") and not criteria.get("min_price"):
        missing.append("price_range")

    has_specific_vehicle = bool(
        criteria.get("make") and criteria.get("model") and criteria.get("year")
    )
    has_broad_vehicle = bool(criteria.get("body_type") or criteria.get("use_case"))

    if not has_specific_vehicle and not has_broad_vehicle:
        missing.append("vehicle_identity")

    if has_broad_vehicle and not criteria.get("max_price"):
        if not criteria.get("year") and not criteria.get("year_min") and not criteria.get("year_max"):
            missing.append("year_or_budget")

    return missing


def _narrowing_guidance(
    criteria: dict[str, Any],
    chat_history: list[dict[str, str]],
) -> dict[str, Any]:
    user_turn_count = _count_user_turns(chat_history)
    allow_zip = user_turn_count >= MIN_USER_TURNS_BEFORE_ZIP
    suggested = "ask_body_type_budget_or_use_case"

    has_model = bool(criteria.get("make") and criteria.get("model"))
    has_year = bool(
        criteria.get("year") or criteria.get("year_min") or criteria.get("year_max")
    )
    has_budget = bool(criteria.get("max_price") or criteria.get("min_price"))

    drive_choices = model_drivetrain_options(criteria.get("make"), criteria.get("model"))
    needs_drivetrain_choice = len(drive_choices) > 1 and not criteria.get("drivetrain")

    if has_model:
        if not has_year:
            suggested = "ask_year_range"
        elif not criteria.get("trim"):
            # Ask real trim names before drivetrain so FWD-only cars never see 4WD chips.
            suggested = "ask_trim"
        elif needs_drivetrain_choice:
            suggested = "ask_drivetrain"
        elif not criteria.get("max_miles"):
            suggested = "ask_max_mileage"
        elif not has_budget:
            suggested = "ask_budget"
        elif allow_zip and not criteria.get("zip_code"):
            suggested = "ask_zip_code"
        else:
            suggested = "ask_features_or_confirm_search"
    elif criteria.get("body_type") or criteria.get("use_case") or criteria.get("max_price"):
        suggested = "ask_model_preference"
    elif allow_zip and not criteria.get("zip_code") and has_year:
        suggested = "ask_zip_code"

    if not allow_zip and suggested == "ask_zip_code":
        if has_model and not has_year:
            suggested = "ask_year_range"
        elif has_model:
            suggested = "ask_trim_or_mileage"
        else:
            suggested = "ask_model_preference"

    return {
        "user_turn_count": user_turn_count,
        "allow_zip_prompt": allow_zip,
        "min_turns_before_zip": MIN_USER_TURNS_BEFORE_ZIP,
        "suggested_next_question": suggested,
        "narrowing_order": [
            "model_or_body_type",
            "year_range",
            "drivetrain_or_trim",
            "max_mileage",
            "price_range_in_5000_increments",
            "zip_code_only_after_min_turns",
        ],
    }


def _merge_criteria(current: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current)
    for key, value in updates.items():
        if key not in PROFILE_FIELDS:
            continue
        if value is None or value == "":
            continue
        merged[key] = value
    return merged


def _normalize_criteria(criteria: dict[str, Any]) -> dict[str, Any]:
    normalized = _merge_criteria(EMPTY_CRITERIA, criteria)

    if normalized.get("drivetrain"):
        drive = str(normalized["drivetrain"]).upper()
        if drive in {"4X4", "AWD", "4WD", "FOUR WHEEL DRIVE"}:
            normalized["drivetrain"] = "4WD"

    if normalized.get("body_type"):
        body = str(normalized["body_type"]).lower().replace("-", " ").strip()
        mapping = {
            "truck": "Pickup",
            "pickup": "Pickup",
            "suv": "SUV",
            "crossover": "SUV",
            "cuv": "SUV",
            "compact suv": "SUV",
            "compact crossover": "SUV",
            "sedan": "Sedan",
            "coupe": "Coupe",
            "hatchback": "Hatchback",
            "van": "Minivan",
            "minivan": "Minivan",
            "mini van": "Minivan",
            "wagon": "Wagon",
        }
        normalized["body_type"] = mapping.get(body, normalized["body_type"])

    # If the model only captured a use_case, promote it to a body type
    # so research can load concrete model cards.
    use_case = str(normalized.get("use_case") or "").lower()
    if not normalized.get("body_type") and any(
        token in use_case for token in ("minivan", "mini van", "van")
    ):
        normalized["body_type"] = "Minivan"
    if not normalized.get("body_type") and any(
        token in use_case for token in ("crossover", "cuv", "compact suv", "suv")
    ):
        normalized["body_type"] = "SUV"

    if normalized.get("make") and normalized.get("model") and normalized.get("year"):
        is_valid, _, canonical = verify_vehicle_exists(
            normalized["make"],
            int(normalized["year"]),
            normalized["model"],
        )
        if is_valid:
            normalized["model"] = canonical

    # Auto-apply drivetrain when the model only has one realistic option (e.g. Prius = FWD).
    if (
        normalized.get("make")
        and normalized.get("model")
        and not normalized.get("drivetrain")
    ):
        drive_choices = model_drivetrain_options(normalized["make"], normalized["model"])
        if len(drive_choices) == 1:
            normalized["drivetrain"] = drive_choices[0]

    return normalized


def _looks_like_vehicle_name(candidate: str, criteria: dict[str, Any]) -> bool:
    """True when a captured 'trim' is actually a year/make/model phrase."""
    text = candidate.lower().strip()
    if not text:
        return True
    if re.search(r"\b20\d{2}\b", text):
        return True
    make = str(criteria.get("make") or "").lower()
    model = str(criteria.get("model") or "").lower()
    if make and make in text:
        return True
    if model:
        model_tokens = [token for token in re.split(r"\s+", model) if len(token) > 2]
        if model_tokens and all(token in text for token in model_tokens):
            return True
    # Long multi-word captures are almost never real trim codes.
    if len(text.split()) >= 3:
        return True
    return False


def _extract_trim_from_message(
    message: str,
    criteria: dict[str, Any],
) -> Optional[str]:
    text = message.lower()
    make = criteria.get("make")
    model = criteria.get("model")
    known = model_trim_options(make, model)

    for trim in known:
        # Require trim token as its own word so "EV" inside model names does not match.
        if re.search(rf"\b{re.escape(trim.lower())}\b", text):
            return trim

    # Map old generic chips / phrasing onto real trim ladders when we know them.
    if known:
        if any(token in text for token in ("base trim", "base-level", "entry trim", "lowest trim")):
            return known[0]
        if any(token in text for token in ("mid trim", "mid-level", "middle trim")):
            return known[min(1, len(known) - 1)]
        if any(token in text for token in ("top trim", "top-level", "highest trim", "fully loaded")):
            return known[-1]

    # Only accept explicit "... TRIM" phrasing — never "interested in the 2021 GMC ..."
    match = re.search(
        r"\b([a-z0-9][a-z0-9\-]{0,20})\s+trim\b",
        text,
    )
    if match:
        candidate = match.group(1).strip(" .,")
        if candidate and candidate not in {"base", "mid", "top", "the", "a"}:
            if not _looks_like_vehicle_name(candidate, criteria):
                return candidate.upper() if len(candidate) <= 4 else candidate.title()
    return None


def _is_broad_vehicle_pivot(message: str, criteria: dict[str, Any]) -> bool:
    """User switched from a focused model to a broad category search."""
    if not (criteria.get("make") and criteria.get("model")):
        return False
    text = message.lower()
    make = str(criteria.get("make") or "").lower()
    model = str(criteria.get("model") or "").lower()
    # Still talking about the same vehicle.
    if make and make in text:
        return False
    if model and model in text:
        return False
    # Distinctive model tokens (ignore short ones like "ev").
    model_tokens = [token for token in re.split(r"[\s\-]+", model) if len(token) > 2]
    if model_tokens and all(token in text for token in model_tokens):
        return False

    intent_markers = (
        "looking for",
        "show me",
        "find me",
        "search for",
        "i want",
        "i need",
        "i am looking",
        "i'm looking",
    )
    category_markers = (
        "suvs",
        "suv that",
        "suvs that",
        "trucks",
        "pickups",
        "sedans",
        "crossovers",
        "electric",
        "evs",
        "hybrids",
        "minivans",
        "cars under",
    )
    has_intent = any(marker in text for marker in intent_markers)
    has_category = any(marker in text for marker in category_markers)
    return has_intent and has_category


def _clear_focused_vehicle(criteria: dict[str, Any]) -> dict[str, Any]:
    cleared = dict(criteria)
    for key in ("make", "model", "year", "year_min", "year_max", "trim", "drivetrain"):
        cleared[key] = None
    return cleared


_VEHICLE_NAME_ALIASES: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\bhummer\s*ev\s*pick[\s-]*up\b", re.I), "GMC", "Hummer EV Pickup"),
    (re.compile(r"\bhummer\s*ev\s*truck\b", re.I), "GMC", "Hummer EV Pickup"),
    (re.compile(r"\bhummer\s*ev\s*suv\b", re.I), "GMC", "Hummer EV SUV"),
    (re.compile(r"\bgmc\s+hummer(?:\s*ev)?\b", re.I), "GMC", "Hummer EV SUV"),
    (re.compile(r"\bhummer\s*ev\b", re.I), "GMC", "Hummer EV SUV"),
    (re.compile(r"\bmustang\s*mach[-\s]?e\b", re.I), "Ford", "Mustang Mach-E"),
    (re.compile(r"\bmach[-\s]?e\b", re.I), "Ford", "Mustang Mach-E"),
    (re.compile(r"\bioniq\s*5\b", re.I), "Hyundai", "Ioniq 5"),
    (re.compile(r"\bid\.?\s*4\b", re.I), "Volkswagen", "ID.4"),
    (re.compile(r"\bmodel\s*y\b", re.I), "Tesla", "Model Y"),
    (re.compile(r"\bmodel\s*3\b", re.I), "Tesla", "Model 3"),
    (re.compile(r"\bf[- ]?150\b", re.I), "Ford", "F-150"),
    (re.compile(r"\bsilverado(?:\s*1500)?\b", re.I), "Chevrolet", "Silverado 1500"),
    (re.compile(r"\bram\s*1500\b", re.I), "Ram", "1500"),
]

_MODEL_LOOKUP_CACHE: Optional[list[tuple[int, str, str, str]]] = None


def _model_lookup_entries() -> list[tuple[int, str, str, str]]:
    """Longest-first (make, model) needles from vehicles.json for message matching."""
    global _MODEL_LOOKUP_CACHE
    if _MODEL_LOOKUP_CACHE is not None:
        return _MODEL_LOOKUP_CACHE

    from app_ai_core import _load_vehicles_db

    db = _load_vehicles_db() or {}
    entries: list[tuple[int, str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for make, years in db.items():
        models: set[str] = set()
        for year_models in years.values():
            if isinstance(year_models, list):
                models.update(str(item) for item in year_models)
        for model in models:
            key = (make, model)
            if key in seen:
                continue
            seen.add(key)
            full = f"{make} {model}".lower()
            entries.append((len(full), make, model, full))
            # Model-only needle when distinctive enough (avoids matching tiny tokens).
            if len(model) >= 5:
                entries.append((len(model), make, model, model.lower()))
    entries.sort(key=lambda item: item[0], reverse=True)
    _MODEL_LOOKUP_CACHE = entries
    return entries


def _extract_make_model_from_message(
    message: str,
    criteria: dict[str, Any],
) -> dict[str, Any]:
    """Pull a concrete make/model from prompts like 'know about the Hummer EV'."""
    if criteria.get("make") and criteria.get("model"):
        return {}

    text = message.strip()
    if not text:
        return {}

    for pattern, make, model in _VEHICLE_NAME_ALIASES:
        if pattern.search(text):
            return {"make": make, "model": model}

    lowered = text.lower()
    # Prefer matches after intent phrasing, but still scan the full message.
    intent = re.search(
        r"(?:know about|tell me about|interested in|looking at|research|about)\s+(?:the\s+)?(.+)$",
        lowered,
    )
    haystacks = [intent.group(1).strip()] if intent else []
    haystacks.append(lowered)

    for haystack in haystacks:
        for _length, make, model, needle in _model_lookup_entries():
            if len(needle) < 5:
                continue
            if needle in haystack:
                return {"make": make, "model": model}
    return {}


def _extract_criteria_from_message(
    message: str,
    criteria: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic capture so follow-up chips actually advance narrowing."""
    updates: dict[str, Any] = {}
    text = message.lower()

    updates.update(_extract_make_model_from_message(message, criteria))
    working = {**criteria, **updates}

    if not working.get("trim"):
        trim = _extract_trim_from_message(message, working)
        if trim:
            updates["trim"] = trim

    if not working.get("drivetrain"):
        for label in ("4wd", "4x4", "awd", "fwd", "rwd"):
            if re.search(rf"\b{label}\b", text):
                updates["drivetrain"] = "4WD" if label in {"4wd", "4x4"} else label.upper()
                break

    miles_match = re.search(r"under\s+(\d[\d,]*)\s*miles", text)
    if miles_match and not working.get("max_miles"):
        updates["max_miles"] = int(miles_match.group(1).replace(",", ""))

    year_match = re.search(r"\b(20\d{2})\b", text)
    if year_match and not working.get("year"):
        updates["year"] = int(year_match.group(1))

    return updates


def _has_model_option_focus(criteria: dict[str, Any]) -> bool:
    """True once the shopper locked a year, trim/engine, or mileage on a model."""
    if not (criteria.get("make") and criteria.get("model")):
        return False
    return bool(
        criteria.get("year")
        or criteria.get("year_min")
        or criteria.get("year_max")
        or criteria.get("trim")
        or criteria.get("max_miles")
    )


def _infer_phase(criteria: dict[str, Any], message: str, research_bundle: dict[str, Any]) -> str:
    text = message.lower()
    if criteria.get("make") and criteria.get("model"):
        if (
            criteria.get("year")
            and criteria.get("zip_code")
            and (criteria.get("min_price") or criteria.get("max_price"))
        ):
            return "search_ready"
        if _has_model_option_focus(criteria):
            return "option_focus"
        return "model_focus"
    if any(
        phrase in text
        for phrase in [
            "tell me about",
            "know about",
            "want to know about",
            "history of",
            "what do people think",
        ]
    ):
        return "brand_or_model_story"
    if research_bundle.get("candidate_models") or research_bundle.get("use_cases_detected"):
        return "discover"
    return "narrow"


def _response_mode(phase: str) -> str:
    if phase in {"model_focus", "brand_or_model_story"}:
        return "model_focus"
    if phase == "option_focus":
        return "option_focus"
    if phase == "search_ready":
        return "search_ready"
    return "discover"


def _research_sections_from_bundle(research_bundle: dict[str, Any]) -> list[dict[str, str]]:
    dive = research_bundle.get("model_deep_dive")
    if not dive:
        return []

    sections: list[dict[str, str]] = []
    years_good = dive.get("years_to_consider") or []
    if years_good:
        sections.append(
            {
                "label": "Years to target",
                "content": ", ".join(str(year) for year in years_good),
            }
        )

    years_bad = dive.get("years_to_scrutinize") or []
    if years_bad:
        sections.append(
            {
                "label": "Years to scrutinize",
                "content": ", ".join(str(year) for year in years_bad),
            }
        )

    recall_rows = dive.get("recalls_by_year") or []
    recall_bits = [
        f"{row['year']}: {row['recall_count']} active"
        for row in sorted(recall_rows, key=lambda item: item["recall_count"], reverse=True)
        if row.get("recall_count", 0) > 0
    ][:4]
    if recall_bits:
        sections.append({"label": "Recalls", "content": "; ".join(recall_bits)})

    competitors = dive.get("competitors") or []
    if competitors:
        sections.append(
            {
                "label": "Also shopped",
                "content": ", ".join(competitors),
            }
        )

    listing = dive.get("sample_listing") or {}
    if listing.get("price"):
        price = listing["price"]
        miles = listing.get("miles")
        miles_text = f", {miles:,} miles" if isinstance(miles, (int, float)) else ""
        sections.append(
            {
                "label": "Market snapshot",
                "content": f"Sample listing near ${price:,.0f}{miles_text}.",
            }
        )

    return sections


def _supplement_model_details(
    model_details: Optional[dict[str, Any]],
    research_bundle: dict[str, Any],
) -> Optional[dict[str, Any]]:
    dive = research_bundle.get("model_deep_dive")
    if not dive:
        return model_details

    base = dict(model_details or {})
    base.setdefault("make", dive["make"])
    base.setdefault("model", dive["model"])
    base.setdefault("overview", "")
    ai_sections = list(base.get("sections") or [])
    ai_labels = {section.get("label", "").lower() for section in ai_sections if section.get("label")}

    merged_sections = list(ai_sections)
    for section in _research_sections_from_bundle(research_bundle):
        if section["label"].lower() not in ai_labels:
            merged_sections.append(section)

    base["sections"] = merged_sections
    return base


def _model_details_text(model_details: Optional[dict[str, Any]]) -> str:
    if not model_details:
        return ""
    parts = [str(model_details.get("overview", ""))]
    for section in model_details.get("sections", []):
        parts.append(f"{section.get('label', '')} {section.get('content', '')}")
    return " ".join(part for part in parts if part)


def _merge_vehicle_summaries(
    highlights: list[dict[str, Any]],
    vehicle_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    lookup: dict[tuple[str, str], str] = {}
    for item in vehicle_summaries:
        make = str(item.get("make", "")).strip()
        model = str(item.get("model", "")).strip()
        sentence = str(item.get("sentence", "")).strip()
        if make and model and sentence:
            lookup[(make.lower(), model.lower())] = sentence

    merged = []
    for highlight in highlights:
        row = dict(highlight)
        key = (row["make"].lower(), row["model"].lower())
        if key in lookup:
            row["summary"] = lookup[key]
        merged.append(row)
    return merged


def _highlights_from_summaries(
    vehicle_summaries: list[dict[str, Any]],
    criteria: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Build image cards from LLM-named models when the research catalog is empty."""
    from vehicle_reference_image import resolve_vehicle_photo

    criteria = criteria or {}
    year = criteria.get("year") or criteria.get("year_max")
    year_value = int(year) if year else None
    highlights: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in vehicle_summaries:
        make = str(item.get("make", "")).strip()
        model = str(item.get("model", "")).strip()
        sentence = str(item.get("sentence", "")).strip()
        if not make or not model:
            continue
        key = (make.lower(), model.lower())
        if key in seen:
            continue
        seen.add(key)
        photo_meta = resolve_vehicle_photo(None, make, model, year_value)
        highlights.append(
            {
                "id": f"{make}-{model}-summary",
                "make": make,
                "model": model,
                "year": year_value,
                "title": f"{make} {model}",
                "photo": photo_meta.get("photo"),
                "photo_source": photo_meta.get("photo_source"),
                "summary": sentence or f"{make} {model} matches your search criteria.",
            }
        )
    return highlights[:4]


def _summaries_text(vehicle_summaries: list[dict[str, Any]]) -> str:
    return " ".join(
        f"{item.get('make', '')} {item.get('model', '')} {item.get('sentence', '')}"
        for item in vehicle_summaries
    )


def _vehicle_names_phrase(vehicle_summaries: list[dict[str, Any]]) -> str:
    names: list[str] = []
    for item in vehicle_summaries:
        make = str(item.get("make", "")).strip()
        model = str(item.get("model", "")).strip()
        if make and model:
            names.append(f"{make} {model}")
    if not names:
        return ""
    if len(names) == 1:
        return f"The {names[0]}"
    if len(names) == 2:
        return f"The {names[0]} and {names[1]}"
    return f"The {', '.join(names[:-1])}, and {names[-1]}"


def _summary_mentions_vehicles(
    summary: str,
    vehicle_summaries: list[dict[str, Any]],
) -> bool:
    text = summary.lower()
    for item in vehicle_summaries:
        make = str(item.get("make", "")).strip().lower()
        model = str(item.get("model", "")).strip().lower()
        if make and model and make in text and model in text:
            return True
    return False


def _normalize_summary_tail(summary: str) -> str:
    text = summary.strip()
    for prefix in ("These ", "these ", "Here are ", "here are "):
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _finalize_response_summary(
    summary: str,
    vehicle_summaries: list[dict[str, Any]],
    response_mode: str,
) -> str:
    if response_mode != "discover" or not vehicle_summaries:
        return summary

    names_phrase = _vehicle_names_phrase(vehicle_summaries)
    if not names_phrase:
        return summary

    if summary and _summary_mentions_vehicles(summary, vehicle_summaries):
        return summary

    tail = _normalize_summary_tail(summary) if summary else ""
    if tail:
        match = re.match(r"^(.+?)\s+are\s+(.+)$", tail, flags=re.IGNORECASE)
        if match:
            subject, predicate = match.groups()
            return f"{names_phrase} are {subject.strip()} {predicate.strip()}"
        return f"{names_phrase} are {tail}"

    return f"{names_phrase} are strong options that match what you're looking for."


def _fallback_response_summary(
    response_mode: str,
    vehicle_summaries: list[dict[str, Any]],
    model_details: Optional[dict[str, Any]],
    user_message: str,
) -> str:
    if response_mode == "discover" and vehicle_summaries:
        names_phrase = _vehicle_names_phrase(vehicle_summaries)
        if names_phrase:
            return f"{names_phrase} are strong options that match what you're looking for."
        return "Here are strong options that match what you're looking for."

    if response_mode == "model_focus" and model_details:
        overview = str(model_details.get("overview", "")).strip()
        if overview:
            return overview

    if response_mode == "option_focus":
        topic = str(user_message).strip().rstrip(".")
        if topic:
            return f"Here is what matters for {topic}."
        return ""

    topic = str(user_message).strip().rstrip(".")
    if topic:
        return f"Here is what stands out for {topic.lower()}."
    return ""


def _count_sentences(text: str) -> int:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text or "") if part.strip()]
    return len(parts)


def _enrich_option_focus_summary(summary: str, criteria: dict[str, Any]) -> str:
    """Guarantee 3+ sentences covering owners and expert/analyst views for THIS option."""
    vehicle = f"{criteria.get('make', '')} {criteria.get('model', '')}".strip() or "this vehicle"
    trim = str(criteria.get("trim") or "").strip()
    if trim and _looks_like_vehicle_name(trim, criteria):
        trim = ""
    year = criteria.get("year")
    option = " ".join(str(part) for part in (year, vehicle, trim) if part).strip() or vehicle

    text = (summary or "").strip()
    lowered = text.lower()
    mentions_owners = any(
        token in lowered for token in ("owner", "owners", "drivers", "people like", "owners say")
    )
    mentions_experts = any(
        token in lowered
        for token in (
            "expert",
            "analyst",
            "reviewer",
            "influencer",
            "critics",
            "automotive press",
            "reviewers",
        )
    )
    mentions_option = (not trim) or trim.lower() in lowered

    extras: list[str] = []
    if trim and not mentions_option:
        extras.append(
            f"The {option} is the specific setup to judge here — feature content, comfort, and price "
            "positioning all change meaningfully versus other trims."
        )
    if not mentions_owners:
        extras.append(
            f"Owners shopping the {option} usually care about real-world efficiency, cabin features at "
            "that trim level, and whether long-term ownership costs stay predictable."
        )
    if not mentions_experts:
        extras.append(
            f"Experts and automotive reviewers typically judge the {option} on value for money, "
            "equipment versus rivals, and any year-specific reliability notes."
        )
    if _count_sentences(text) + len(extras) < 3:
        extras.append(
            f"Before buying a {option}, confirm service history and have a pre-purchase inspection focused "
            "on that configuration."
        )

    if extras:
        text = " ".join(part for part in [text, *extras] if part).strip()
    return text


def process_assistant_turn(
    message: str,
    criteria: Optional[dict[str, Any]] = None,
    history: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    current = _normalize_criteria(criteria or EMPTY_CRITERIA)
    # Broad pivots like "looking for SUVs that are EVs" should leave a prior model focus.
    if _is_broad_vehicle_pivot(message, current):
        current = _normalize_criteria(_clear_focused_vehicle(current))
    # Resolve named vehicles before research so "Hummer EV" doesn't become a generic EV list.
    current = _normalize_criteria(
        _merge_criteria(current, _extract_make_model_from_message(message, current))
    )
    chat_history = history or []
    user_turn_count = _count_user_turns(chat_history)
    narrowing = _narrowing_guidance(current, chat_history)
    research_bundle = build_research_bundle(current, message)
    phase = _infer_phase(current, message, research_bundle)

    system_prompt = """
You are Carvest, a premium automotive research assistant.

Use phase_hint to choose the response shape.

## DISCOVER / NARROW (broad first prompt — compare options)
- response_mode: "discover"
- response_summary: 1-2 sentences introducing the recommendations (shown above vehicle cards).
  MUST name every recommended make/model (e.g. "The Ford F-150, Toyota Tacoma, and Ram 1500 are reliable pickups well-regarded for durability.").
  Never use vague openers like "These reliable pickups" without naming the models.
- vehicle_summaries: 2-4 models from research_bundle.candidate_models.
  Each entry is exactly ONE sentence (max 25 words) tailored to the user's request.
- model_details: null
- assistant_message: exactly ONE sentence follow-up. Use narrowing_guidance.suggested_next_question.
  NEVER ask for ZIP code unless narrowing_guidance.allow_zip_prompt is true.

Narrowing order (price and ZIP are the final search-preparation steps):
1. Model preference (if broad search)
2. Year or year range
3. Drivetrain, trim, or max mileage
4. Price range in exact $5,000 increments
5. ZIP code — immediately after price, and only after min_turns_before_zip user messages

Example — "I want a 4x4 truck under $35,000":
vehicle_summaries: Ford F-150, Toyota Tacoma, Chevrolet Silverado 1500 (one sentence each)
assistant_message: "Which of these models interests you most?"

## MODEL_FOCUS / BRAND_OR_MODEL_STORY (user picked a model, no year/trim/mileage yet)
Use this when phase_hint is model_focus or brand_or_model_story — e.g.
"I'm interested in the Toyota Tundra. Tell me which years are best and what to avoid."
- response_mode: "model_focus"
- response_summary: optional 1-sentence hook; model_details.overview is shown if empty.
- vehicle_summaries: [] (empty)
- model_details: REQUIRED deep dive for the focused make/model using research_bundle.model_deep_dive.
  {
    "make": "Toyota",
    "model": "Tundra",
    "overview": "One hook sentence.",
    "sections": [
      {"label": "Positioning", "content": "1-2 sentences."},
      {"label": "Generations", "content": "1-2 sentences on model history."},
      {"label": "Common features", "content": "1-2 sentences on trims/features."},
      {"label": "What owners like", "content": "1-2 sentences."},
      {"label": "What to watch", "content": "1-2 sentences on drawbacks or concerns."}
    ]
  }
- Use recalls_by_year, years_to_consider, years_to_scrutinize from research_bundle when relevant.
- Mention competitor makes/models clearly in sections (Also shopped) — they will appear as cards.
- assistant_message: ONE sentence follow-up from narrowing_guidance. Do NOT ask ZIP unless allow_zip_prompt is true.
- follow_up_options: 4-6 clickable bubbles that MUST match narrowing_guidance.suggested_next_question.
  ask_budget -> $5,000 range chips like $20k–$25k, $25k–$30k, $30k–$35k.
  When selected, capture BOTH min_price and max_price from the range.
  ask_year_range -> year chips like 2022, 2021, 2020
  ask_trim -> trim/engine chips for the focused model
  ask_drivetrain -> 4WD, AWD, FWD, RWD
  ask_max_mileage -> Under 50k, Under 75k, Under 100k
  ask_zip_code -> Enter ZIP in chat
  Example for Ram 1500 when ask_trim: [{"label":"TRX","message":"I'm interested in the Ram 1500 TRX trim"},{"label":"5.7L Hemi","message":"Tell me about the Ram 1500 with the 5.7L Hemi engine"}]
  Do NOT write a long either/or question in assistant_message when follow_up_options are provided.

## OPTION_FOCUS (user already picked year, trim/engine, and/or mileage on a model)
Use this when phase_hint is option_focus — e.g. they chose 2021, TRD, Under 50k miles, or a specific engine.
- response_mode: "option_focus"
- model_details: null  (NEVER repeat the broad Positioning/Generations overview)
- vehicle_summaries: []
- response_summary: REQUIRED — at least 3 full sentences ONLY about the selected year/trim/engine/mileage.
  Must include all of the following (can span the 3+ sentences):
  1) Practical ownership notes / what to inspect for THAT option
  2) What everyday owners/drivers tend to say they like or dislike about that option
  3) What experts, analysts, or automotive influencers/reviewers generally say about that option
  Do not rehash the full model history. Stay specific to the chosen year/trim/engine/mileage.
  If trim is set (e.g. Prius LE), name that trim in the summary — do not reuse the prior year-only blurb.
- Capture the selection in criteria_updates (year, trim, max_miles, drivetrain as appropriate).
  Important: when the user picks a trim chip, set criteria_updates.trim to the exact trim name (LE, XLE, Limited, etc.).
  Never invent drivetrains the model does not offer (e.g. do not assign 4WD to a Toyota Prius).
- assistant_message: ONE sentence follow-up from narrowing_guidance for the NEXT missing detail.
  Do NOT repeat the same question the user just answered.
- follow_up_options: 4-6 chips for the next narrowing step only.
  For ask_trim, use real trim names for that model (Prius => LE, XLE, Limited) — never Base/Mid/Top.

## SEARCH_READY
- response_mode: "search_ready"
- vehicle_summaries: []
- model_details: null
- assistant_message: ONE sentence telling the user listings are loading.

## Rules
- Use research_bundle facts; do not invent recall counts.
- Set ready_to_search true only when zip_code and a price range exist, enough vehicle criteria exist, and narrowing is complete.
- Do NOT ask for ZIP until narrowing_guidance.allow_zip_prompt is true (after several user messages).
- Capture make/model in criteria_updates when the user picks a model.
- If the user names ONE specific vehicle (e.g. "Hummer EV", "Toyota Prius"), use model_focus
  for that vehicle. Do NOT substitute a generic EV/SUV comparison list.
- Always include follow_up_options (4-6 items) unless ready_to_search is true.

Return ONLY valid JSON:
{
  "criteria_updates": { ...same fields, null if unknown... },
  "response_mode": "discover|model_focus|option_focus|search_ready",
  "response_summary": "1-2 sentence intro shown above vehicle cards.",
  "vehicle_summaries": [{"make": "Ford", "model": "F-150", "sentence": "One sentence."}],
  "model_details": null,
  "follow_up_options": [{"label": "2022", "message": "Tell me about the 2022 Ram 1500"}],
  "assistant_message": "Pick an option below or type your own reply.",
  "phase": "discover|narrow|model_focus|option_focus|brand_or_model_story|search_ready",
  "ready_to_search": false
}
"""

    user_payload = {
        "current_criteria": current,
        "conversation_history": chat_history[-10:],
        "latest_user_message": message,
        "missing_fields": _missing_for_search(
            current,
            require_zip=narrowing["allow_zip_prompt"],
        ),
        "narrowing_guidance": narrowing,
        "phase_hint": phase,
        "research_bundle": research_bundle,
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, indent=2)},
        ],
        temperature=0.45,
    )

    raw = json.loads(response.choices[0].message.content or "{}")
    updated = _normalize_criteria(_merge_criteria(current, raw.get("criteria_updates", {})))
    # Capture trim/year/drivetrain from chip text even if the model forgets criteria_updates.
    updated = _normalize_criteria(
        _merge_criteria(updated, _extract_criteria_from_message(message, updated))
    )
    narrowing = _narrowing_guidance(updated, chat_history)
    missing = _missing_for_search(
        updated,
        require_zip=narrowing["allow_zip_prompt"],
    )
    missing_for_ready = _missing_for_search(updated, require_zip=True)
    ready = raw.get("ready_to_search", False) and not missing_for_ready
    # Server-side phase wins over the model so overview vs option-focus stays consistent.
    response_phase = _infer_phase(updated, message, research_bundle)
    if ready:
        response_phase = "search_ready"
    response_mode = _response_mode(response_phase)
    updated_research = (
        research_bundle
        if updated == current
        else build_research_bundle(updated, message)
    )
    vehicle_summaries = raw.get("vehicle_summaries", [])
    model_details = _supplement_model_details(raw.get("model_details"), updated_research)

    # Broad model pick → keep the full overview panel + image.
    # Year/trim/mileage/engine pick → drop the broad overview and stay option-focused.
    if response_mode == "option_focus":
        model_details = None
        vehicle_summaries = []
    elif response_mode == "model_focus":
        vehicle_summaries = []
        if model_details and not model_details.get("sections"):
            model_details = _supplement_model_details(model_details, updated_research)

    highlights = _merge_vehicle_summaries(
        build_highlights(updated_research, updated),
        vehicle_summaries,
    )
    # Prefer models the LLM named so cards match the intro text
    # (e.g. Mach-E / Ioniq 5 instead of generic RAV4/CR-V catalog picks).
    if response_mode == "discover" and vehicle_summaries:
        summary_highlights = _highlights_from_summaries(vehicle_summaries, updated)
        if summary_highlights:
            highlights = summary_highlights
    elif not highlights and vehicle_summaries:
        highlights = _highlights_from_summaries(vehicle_summaries, updated)
    if (
        not highlights
        and response_mode in {"model_focus", "option_focus"}
        and updated.get("make")
        and updated.get("model")
    ):
        highlights = _highlights_from_summaries(
            [
                {
                    "make": updated["make"],
                    "model": updated["model"],
                    "sentence": str(raw.get("response_summary", "")).strip(),
                }
            ],
            updated,
        )
    # Keep the focused trim/year visible on the option card title.
    if response_mode == "option_focus" and highlights:
        clean_trim = updated.get("trim")
        if clean_trim and _looks_like_vehicle_name(str(clean_trim), updated):
            clean_trim = None
            updated["trim"] = None
        for highlight in highlights:
            if clean_trim:
                highlight["trim"] = clean_trim
            else:
                highlight.pop("trim", None)
            if updated.get("year"):
                highlight["year"] = updated["year"]
            title_bits = [
                highlight.get("year"),
                highlight.get("make"),
                highlight.get("model"),
            ]
            if clean_trim:
                title_bits.append(clean_trim)
            highlight["title"] = " ".join(str(bit) for bit in title_bits if bit)
    if model_details and response_mode == "model_focus":
        overview = str(model_details.get("overview", "")).strip()
        for highlight in highlights:
            if overview:
                highlight["summary"] = overview

    assistant_message = raw.get(
        "assistant_message",
        "Tell me what kind of vehicle lifestyle you are shopping for.",
    )
    mention_text = " ".join(
        part
        for part in [
            assistant_message,
            str(raw.get("response_summary", "")),
            _summaries_text(vehicle_summaries),
            _model_details_text(model_details),
        ]
        if part
    )
    # Competitors only on the broad model overview — keep option focus tight.
    competitor_highlights: list[dict[str, Any]] = []
    if response_mode == "model_focus":
        competitor_highlights = build_competitor_highlights(
            updated_research,
            updated,
            mention_text,
            highlights,
        )
        competitor_highlights = _merge_vehicle_summaries(
            competitor_highlights,
            vehicle_summaries,
        )
    follow_up = build_follow_up_options(
        updated,
        updated_research,
        narrowing,
        raw.get("follow_up_options"),
        highlights,
        response_mode,
    )
    follow_up_options = follow_up["options"]
    follow_up_prompt = follow_up["prompt"]
    if follow_up_options and not ready:
        assistant_message = follow_up_prompt

    response_summary = str(raw.get("response_summary", "")).strip()
    if not response_summary:
        response_summary = _fallback_response_summary(
            response_mode,
            vehicle_summaries,
            model_details,
            message,
        )
    response_summary = _finalize_response_summary(
        response_summary,
        vehicle_summaries,
        response_mode,
    )
    if response_mode == "option_focus":
        if not response_summary:
            vehicle = f"{updated.get('make', '')} {updated.get('model', '')}".strip()
            focus_bits = []
            if updated.get("year"):
                focus_bits.append(str(updated["year"]))
            elif updated.get("year_max") or updated.get("year_min"):
                focus_bits.append(
                    f"{updated.get('year_min') or ''}-{updated.get('year_max') or ''}".strip("-")
                )
            if updated.get("trim"):
                focus_bits.append(str(updated["trim"]))
            if updated.get("max_miles"):
                focus_bits.append(f"under {int(updated['max_miles']):,} miles")
            focus_label = " ".join(focus_bits) or "selected options"
            response_summary = (
                f"Focusing on the {focus_label} {vehicle}. "
                "Here is what matters most for that specific choice."
            )
        response_summary = _enrich_option_focus_summary(response_summary, updated)

    return {
        "criteria": updated,
        "profile_text": _format_profile_text(updated),
        "assistant_message": assistant_message,
        "response_summary": response_summary,
        "phase": response_phase,
        "response_mode": response_mode,
        "highlights": highlights,
        "competitor_highlights": competitor_highlights,
        "model_details": model_details,
        "follow_up_options": follow_up_options,
        "follow_up_prompt": follow_up_prompt,
        "research_bundle": updated_research,
        "ready_to_search": ready,
        "missing_fields": missing,
        "narrowing_guidance": narrowing,
    }
