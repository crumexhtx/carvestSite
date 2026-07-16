import os
import sys
import time
from typing import Any, Optional

import env_setup  # noqa: F401
import requests

from cache_backend import build_cache_key, get_json, set_json

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "https://api.marketcheck.com/v2"
DEFAULT_TIMEOUT = float(os.environ.get("MARKETCHECK_TIMEOUT_SECONDS", "12"))
DEFAULT_RETRIES = max(0, int(os.environ.get("MARKETCHECK_MAX_RETRIES", "2")))
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class MarketCheckError(Exception):
    pass


def get_api_key() -> str:
    api_key = os.environ.get("MARKETCHECK_API_KEY", "").strip()
    if not api_key:
        raise MarketCheckError(
            "MARKETCHECK_API_KEY is not set. Sign up at https://www.marketcheck.com/apis/ "
            "and add your key to the environment."
        )
    return api_key


def _cache_ttl(path: str, params: dict[str, Any]) -> int:
    if path.startswith("/predict/"):
        return int(os.environ.get("MARKETCHECK_PREDICTION_TTL_SECONDS", "21600"))
    if (
        path == "/search/car/active"
        and int(params.get("rows", 0) or 0) == 1
        and str(params.get("photo_links", "")).lower() == "false"
    ):
        return int(os.environ.get("MARKETCHECK_INVENTORY_TTL_SECONDS", "21600"))
    return int(os.environ.get("MARKETCHECK_SEARCH_TTL_SECONDS", "900"))


def _request(path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    public_query = dict(params or {})
    cache_key = build_cache_key(
        "marketcheck:v1",
        {"path": path, "params": public_query},
    )
    cached = get_json(cache_key)
    if isinstance(cached, dict):
        print(f"MarketCheck cache hit for {path}", flush=True)
        return cached

    query = dict(public_query)
    query["api_key"] = get_api_key()
    response: Optional[requests.Response] = None
    last_error: Optional[Exception] = None

    for attempt in range(DEFAULT_RETRIES + 1):
        try:
            response = requests.get(
                f"{BASE_URL}{path}",
                params=query,
                timeout=DEFAULT_TIMEOUT,
            )
            if response.status_code not in RETRYABLE_STATUS_CODES:
                break
            if attempt >= DEFAULT_RETRIES:
                break
            retry_after = response.headers.get("Retry-After")
            try:
                delay = min(float(retry_after), 5.0) if retry_after else 0.5 * (2**attempt)
            except (TypeError, ValueError):
                delay = 0.5 * (2**attempt)
            time.sleep(delay)
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= DEFAULT_RETRIES:
                raise MarketCheckError(f"MarketCheck request failed for {path}: {exc}") from exc
            time.sleep(0.5 * (2**attempt))

    if response is None:
        raise MarketCheckError(f"MarketCheck request failed for {path}: {last_error}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise MarketCheckError(f"MarketCheck returned non-JSON response for {path}") from exc

    if not response.ok:
        message = payload.get("message") or payload.get("error") or response.text
        raise MarketCheckError(f"MarketCheck API error ({response.status_code}): {message}")

    set_json(cache_key, payload, _cache_ttl(path, public_query))
    return payload


def normalize_listing(item: dict[str, Any]) -> dict[str, Any]:
    media = item.get("media") or {}
    dealer = item.get("dealer") or {}
    photos = media.get("photo_links_cached") or media.get("photo_links") or []

    return {
        "listing_id": item.get("id"),
        "vin": item.get("vin"),
        "price": item.get("price"),
        "miles": item.get("miles"),
        "heading": item.get("heading"),
        "exterior_color": item.get("exterior_color"),
        "fuel_type": item.get("fuel_type"),
        "dealer_name": dealer.get("name"),
        "city": dealer.get("city"),
        "state": dealer.get("state"),
        "zip": dealer.get("zip"),
        "vdp_url": item.get("vdp_url"),
        "primary_photo": photos[0] if photos else None,
        "photo_count": len(photos),
        "dom": item.get("dom"),
    }


def search_active_listings(
    make: str,
    model: str,
    year: int,
    zip_code: Optional[str] = None,
    radius: int = 100,
    rows: int = 24,
    start: int = 0,
    car_type: str = "used",
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "make": make,
        "model": model,
        "year": str(year),
        "car_type": car_type,
        "photo_links": "true",
        "append_api_key": "false",
        "rows": min(max(rows, 1), 50),
        "start": max(start, 0),
        "stats": "price,miles",
        "sort_by": "price",
        "sort_order": "asc",
    }

    if zip_code:
        params["zip"] = zip_code
        params["radius"] = radius
        params["sort_by"] = "dist"

    print(f"Searching MarketCheck listings for {year} {make} {model}...", flush=True)
    data = _request("/search/car/active", params)
    listings = [normalize_listing(item) for item in data.get("listings", [])]

    return {
        "total_found": data.get("num_found", len(listings)),
        "market_stats": data.get("stats", {}),
        "listings": listings,
        "search_context": {
            "zip": zip_code,
            "radius_miles": radius if zip_code else None,
            "car_type": car_type,
            "start": start,
            "rows": params["rows"],
        },
    }


def predict_market_price(
    vin: str,
    miles: int,
    zip_code: str,
    dealer_type: str = "franchise",
    include_comparables: bool = False,
) -> dict[str, Any]:
    endpoint = "/predict/car/us/marketcheck_price"
    if include_comparables:
        endpoint = "/predict/car/us/marketcheck_price/comparables"

    data = _request(
        endpoint,
        {
            "vin": vin,
            "miles": miles,
            "dealer_type": dealer_type,
            "zip": zip_code,
        },
    )

    predicted_price = (
        data.get("marketcheck_price")
        or data.get("predicted_price")
        or data.get("price")
    )

    return {
        "vin": vin,
        "miles": miles,
        "predicted_price": predicted_price,
        "msrp": data.get("msrp"),
        "comparables_count": len(data.get("comparables", []) or data.get("listings", []) or []),
        "raw": data,
    }


def enrich_listings_with_pricing(
    listings: list[dict[str, Any]],
    zip_code: str,
    max_predictions: int = 3,
) -> list[dict[str, Any]]:
    enriched = []

    for listing in listings:
        row = dict(listing)
        vin = row.get("vin")
        miles = row.get("miles")
        price = row.get("price")

        if (
            vin
            and miles is not None
            and len([item for item in enriched if item.get("price_analysis")]) < max_predictions
        ):
            try:
                prediction = predict_market_price(vin=vin, miles=int(miles), zip_code=zip_code)
                predicted_price = prediction.get("predicted_price")
                if predicted_price is not None and price is not None:
                    row["price_analysis"] = {
                        "predicted_fair_price": predicted_price,
                        "listing_price": price,
                        "price_delta": round(price - predicted_price, 2),
                        "deal_signal": _deal_signal(price, predicted_price),
                    }
            except MarketCheckError as exc:
                row["price_analysis_error"] = str(exc)

        enriched.append(row)

    return enriched


def _deal_signal(listing_price: float, predicted_price: float) -> str:
    delta = listing_price - predicted_price
    if delta <= -1500:
        return "LIKELY_GOOD_DEAL"
    if delta >= 1500:
        return "LIKELY_OVERPRICED"
    return "NEAR_MARKET"


def _build_search_params(
    criteria: dict[str, Any],
    *,
    rows: int,
    start: int,
    radius: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "car_type": "used",
        "photo_links": "true",
        "append_api_key": "false",
        "rows": min(max(rows, 1), 50),
        "start": max(start, 0),
        "stats": "price,miles",
        "sort_by": "price",
        "sort_order": "asc",
    }

    if criteria.get("make"):
        params["make"] = criteria["make"]
    if criteria.get("model"):
        params["model"] = criteria["model"]
    if criteria.get("year"):
        params["year"] = str(criteria["year"])
    elif criteria.get("year_min") or criteria.get("year_max"):
        low = int(criteria.get("year_min") or criteria.get("year_max") or 0)
        high = int(criteria.get("year_max") or criteria.get("year_min") or low)
        if low and high:
            params["year_range"] = f"{min(low, high)}-{max(low, high)}"
    if criteria.get("zip_code"):
        params["zip"] = criteria["zip_code"]
        params["radius"] = radius
        params["sort_by"] = "dist"
    if criteria.get("body_type"):
        params["body_type"] = criteria["body_type"]
    if criteria.get("drivetrain"):
        params["drivetrain"] = criteria["drivetrain"]
    if criteria.get("doors"):
        params["doors"] = str(criteria["doors"])
    if criteria.get("fuel_type"):
        params["fuel_type"] = criteria["fuel_type"]

    min_price = criteria.get("min_price")
    max_price = criteria.get("max_price")
    if min_price or max_price:
        low = int(min_price or 0)
        high = int(max_price or 250000)
        params["price_range"] = f"{low}-{high}"

    max_miles = criteria.get("max_miles")
    if max_miles:
        params["miles_range"] = f"0-{int(max_miles)}"

    min_mpg = criteria.get("min_mpg")
    if min_mpg:
        params["highway_mpg_range"] = f"{int(min_mpg)}-60"

    return params


def _closest_search_attempts(
    criteria: dict[str, Any],
    radius: int,
) -> list[dict[str, Any]]:
    """Progressively relax filters when the exact combo has no inventory."""
    attempts: list[dict[str, Any]] = []

    def add(
        next_criteria: dict[str, Any],
        relaxed: list[str],
        next_radius: Optional[int] = None,
    ) -> None:
        attempts.append(
            {
                "criteria": next_criteria,
                "relaxed": relaxed,
                "radius": next_radius if next_radius is not None else radius,
            }
        )

    base = dict(criteria)

    if base.get("year"):
        year = int(base["year"])
        nearby = dict(base)
        nearby.pop("year", None)
        nearby["year_min"] = year - 1
        nearby["year_max"] = year + 1
        add(nearby, ["nearby years (±1)"])

        wider = dict(base)
        wider.pop("year", None)
        wider["year_min"] = year - 2
        wider["year_max"] = year + 2
        add(wider, ["nearby years (±2)"])

    if base.get("drivetrain"):
        loosened = dict(base)
        loosened.pop("drivetrain", None)
        add(loosened, ["drivetrain"])

    if base.get("max_miles"):
        looser_miles = dict(base)
        looser_miles["max_miles"] = int(int(base["max_miles"]) * 1.5)
        add(looser_miles, ["higher mileage allowance"])
        no_miles = dict(base)
        no_miles.pop("max_miles", None)
        add(no_miles, ["mileage limit"])

    if base.get("min_price") or base.get("max_price"):
        wider_budget = dict(base)
        if base.get("min_price"):
            wider_budget["min_price"] = max(0, int(int(base["min_price"]) * 0.85))
        if base.get("max_price"):
            wider_budget["max_price"] = int(int(base["max_price"]) * 1.15)
        add(wider_budget, ["wider budget"])

    if base.get("zip_code"):
        add(dict(base), ["wider search radius"], next_radius=max(radius, 250))
        add(dict(base), ["much wider search radius"], next_radius=max(radius, 500))

    if base.get("year") or base.get("year_min") or base.get("year_max"):
        any_year = dict(base)
        any_year.pop("year", None)
        any_year.pop("year_min", None)
        any_year.pop("year_max", None)
        add(any_year, ["year filter"])

    if base.get("make") and base.get("model"):
        core = {
            "make": base.get("make"),
            "model": base.get("model"),
            "zip_code": base.get("zip_code"),
        }
        add(
            core,
            ["price, mileage, year, and drivetrain filters"],
            next_radius=max(radius, 500),
        )

    return attempts


def search_by_criteria(
    criteria: dict[str, Any],
    rows: int = 24,
    start: int = 0,
    radius: int = 100,
    enrich_prices: bool = True,
    max_price_predictions: int = 3,
    allow_closest: bool = True,
) -> dict[str, Any]:
    def run_once(active_criteria: dict[str, Any], active_radius: int) -> dict[str, Any]:
        params = _build_search_params(
            active_criteria,
            rows=rows,
            start=start,
            radius=active_radius,
        )
        label_parts = [
            str(active_criteria.get("year") or ""),
            str(active_criteria.get("make") or ""),
            str(
                active_criteria.get("model")
                or active_criteria.get("body_type")
                or "vehicles"
            ),
        ]
        print(
            f"Searching MarketCheck for {' '.join(p for p in label_parts if p).strip()}...",
            flush=True,
        )

        data = _request("/search/car/active", params)
        listings = [normalize_listing(item) for item in data.get("listings", [])]

        if enrich_prices and active_criteria.get("zip_code") and listings:
            listings = enrich_listings_with_pricing(
                listings,
                zip_code=active_criteria["zip_code"],
                max_predictions=min(max_price_predictions, len(listings)),
            )

        return {
            "total_found": data.get("num_found", len(listings)),
            "market_stats": data.get("stats", {}),
            "listings": listings,
            "search_context": {
                **active_criteria,
                "start": start,
                "rows": params["rows"],
                "radius": active_radius if active_criteria.get("zip_code") else None,
            },
        }

    exact = run_once(criteria, radius)
    exact_count = int(exact.get("total_found") or len(exact.get("listings") or []))
    if exact_count > 0 or not allow_closest or start > 0:
        exact["match_quality"] = "exact"
        exact["match_notice"] = None
        exact["relaxed_filters"] = []
        exact["requested_criteria"] = criteria
        exact["applied_criteria"] = criteria
        return exact

    for attempt in _closest_search_attempts(criteria, radius):
        closest = run_once(attempt["criteria"], int(attempt["radius"]))
        closest_count = int(closest.get("total_found") or len(closest.get("listings") or []))
        if closest_count <= 0:
            continue
        relaxed = attempt["relaxed"]
        relaxed_text = ", ".join(relaxed)
        closest["match_quality"] = "closest"
        closest["match_notice"] = (
            "These are the results closest to what you're looking for. "
            f"We loosened {relaxed_text} because no exact matches were available."
        )
        closest["relaxed_filters"] = relaxed
        closest["requested_criteria"] = criteria
        closest["applied_criteria"] = attempt["criteria"]
        return closest

    exact["match_quality"] = "none"
    exact["match_notice"] = (
        "No live listings matched this search, even after looking for the closest options."
    )
    exact["relaxed_filters"] = []
    exact["requested_criteria"] = criteria
    exact["applied_criteria"] = criteria
    return exact


def get_market_snapshot(
    make: str,
    model: str,
    year: int,
    zip_code: Optional[str] = None,
    radius: int = 50,
    max_listings: int = 10,
    max_price_predictions: int = 3,
) -> dict[str, Any]:
    snapshot = search_active_listings(
        make=make,
        model=model,
        year=year,
        zip_code=zip_code,
        radius=radius,
        rows=max_listings,
    )

    if zip_code and snapshot["listings"]:
        snapshot["listings"] = enrich_listings_with_pricing(
            snapshot["listings"],
            zip_code=zip_code,
            max_predictions=max_price_predictions,
        )

    return snapshot


if __name__ == "__main__":
    sample = get_market_snapshot(
        make="Ford",
        model="Explorer",
        year=2015,
        zip_code="90210",
        max_listings=5,
    )

    print("\n--- MARKETCHECK TEST RESULTS ---")
    print(f"Total listings found: {sample['total_found']}")
    print(f"Returned listings: {len(sample['listings'])}")
    if sample.get("market_stats"):
        print(f"Market stats: {sample['market_stats']}")
    if sample["listings"]:
        first = sample["listings"][0]
        print(f"Sample listing: {first.get('heading')} - ${first.get('price')}")
        if first.get("primary_photo"):
            print(f"Sample photo: {first['primary_photo']}")
