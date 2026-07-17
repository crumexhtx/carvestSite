import json
import sys
from pathlib import Path
from typing import Any, Optional

import env_setup  # noqa: F401

from app_ai_core import verify_vehicle_exists
from competitors import get_competitors, resolve_competitor_models
from fetch_marketcheck import MarketCheckError, get_market_snapshot
from fetch_recalls import get_live_recalls
from openai_client import client

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _market_summary(market_data: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not market_data:
        return {
            "listings_found": 0,
            "avg_price": None,
            "avg_miles": None,
            "sample_deal_signals": [],
        }

    stats = market_data.get("market_stats") or {}
    price_stats = stats.get("price") or {}
    miles_stats = stats.get("miles") or {}

    deal_signals = []
    for listing in market_data.get("listings", []):
        analysis = listing.get("price_analysis")
        if analysis:
            deal_signals.append(analysis.get("deal_signal"))

    return {
        "listings_found": market_data.get("total_found", 0),
        "avg_price": price_stats.get("mean"),
        "min_price": price_stats.get("min"),
        "max_price": price_stats.get("max"),
        "avg_miles": miles_stats.get("mean"),
        "sample_deal_signals": deal_signals[:3],
        "top_listings": market_data.get("listings", [])[:3],
    }


def gather_vehicle_intel(
    make: str,
    year: int,
    model: str,
    zip_code: Optional[str] = None,
    role: str = "target",
    max_listings: int = 5,
    max_price_predictions: int = 1,
) -> dict[str, Any]:
    is_valid, message, canonical_make, canonical_model = verify_vehicle_exists(
        make, year, model
    )
    if not is_valid:
        return {
            "role": role,
            "make": make,
            "model": model,
            "year": year,
            "verified": False,
            "error": message,
        }

    print(
        f"Gathering intel for {role}: {year} {canonical_make} {canonical_model}...",
        flush=True,
    )

    recalls = get_live_recalls(canonical_make, year, canonical_model)
    market_data = None
    market_error = None

    if zip_code:
        try:
            market_data = get_market_snapshot(
                make=canonical_make,
                model=canonical_model,
                year=year,
                zip_code=zip_code,
                max_listings=max_listings,
                max_price_predictions=max_price_predictions,
            )
        except MarketCheckError as exc:
            market_error = str(exc)

    return {
        "role": role,
        "make": canonical_make,
        "model": canonical_model,
        "year": year,
        "verified": True,
        "recalls": recalls,
        "market": _market_summary(market_data),
        "market_error": market_error,
    }


def build_comparison_dataset(
    profile: dict[str, Any],
    competitor_limit: int = 4,
) -> dict[str, Any]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    make = profile["make"]
    year = int(profile["year"])
    model = profile["model"]
    zip_code = profile.get("zip_code")

    competitor_lookup = get_competitors(make, model, limit=competitor_limit)
    resolved_competitors = resolve_competitor_models(
        make,
        model,
        year,
        verify_vehicle_exists,
        limit=competitor_limit,
    )

    target = gather_vehicle_intel(
        make=make,
        year=year,
        model=model,
        zip_code=zip_code,
        role="target",
        max_listings=6,
        max_price_predictions=2,
    )

    ordered: list[Optional[dict[str, Any]]] = [None] * len(resolved_competitors)
    verified_jobs: list[tuple[int, dict[str, Any]]] = []
    for idx, candidate in enumerate(resolved_competitors):
        if not candidate.get("verified"):
            ordered[idx] = {
                "role": "competitor",
                "make": candidate["make"],
                "model": candidate["model"],
                "year": year,
                "verified": False,
                "error": candidate.get("error"),
            }
            continue
        verified_jobs.append((idx, candidate))

    if verified_jobs:
        max_workers = min(3, len(verified_jobs))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {
                pool.submit(
                    gather_vehicle_intel,
                    make=candidate["make"],
                    year=year,
                    model=candidate["model"],
                    zip_code=zip_code,
                    role="competitor",
                    max_listings=4,
                    max_price_predictions=1,
                ): idx
                for idx, candidate in verified_jobs
            }
            for future in as_completed(future_map):
                ordered[future_map[future]] = future.result()

    competitors = [row for row in ordered if row is not None]

    return {
        "target_profile": profile,
        "segment": competitor_lookup.get("segment"),
        "people_also_shop": competitor_lookup.get("people_also_shop", []),
        "target": target,
        "competitors": competitors,
    }


def generate_comparison_report(
    profile: dict[str, Any],
    competitor_limit: int = 4,
    dataset: Optional[dict[str, Any]] = None,
) -> str:
    is_valid, message, canonical_make, canonical_model = verify_vehicle_exists(
        profile["make"],
        int(profile["year"]),
        profile["model"],
    )
    if not is_valid:
        return f"Error: {message}"
    profile = {**profile, "make": canonical_make, "model": canonical_model}

    if dataset is None:
        dataset = build_comparison_dataset(profile, competitor_limit=competitor_limit)

    system_instruction = (
        "You are Carvest, an expert automotive comparison analyst. "
        "Use only the provided structured data. Compare vehicles objectively across safety, "
        "recall exposure, local market pricing, and buyer value. Be concise and data-driven."
    )

    user_prompt = f"""
    Compare the shopper's target vehicle against its competitive set and shoppers-also-consider alternatives.

    Target Vehicle Profile:
    {json.dumps(profile, indent=2)}

    Comparison Dataset:
    {json.dumps(dataset, indent=2)}

    Format your response EXACTLY in Markdown with these sections and no intro/outro text:

    ### 🔄 COMPETITIVE LANDSCAPE
    [2-3 sentences on the segment and why these rivals matter]

    ### 👥 PEOPLE ALSO SHOP
    [Bullet list of alternative models shoppers commonly cross-shop, using the dataset]

    ### 📊 SIDE-BY-SIDE COMPARISON
    [Markdown table with columns: Vehicle | Listings Found | Avg Price | Avg Miles | Recalls | Deal Signal | Best For]

    ### 🏆 CARVEST VERDICT
    * **Best Value Pick:** [One model and why, based on pricing/recalls data]
    * **Safest Pick:** [One model and why, based on recall severity/count]
    * **Stick With Target If:** [When the searched vehicle still makes sense]
    * **Switch To Alternative If:** [Specific trigger conditions from the data]

    ### 📉 NEGOTIATION EDGE
    [One paragraph on how to use competitor pricing/recall differences while negotiating]
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as exc:
        return f"Failed to connect to AI Engine: {exc}"


def run_comparison(profile_path: Path) -> str:
    with open(profile_path, encoding="utf-8") as handle:
        profile = json.load(handle)
    return generate_comparison_report(profile)


if __name__ == "__main__":
    default = Path(__file__).parent / "exampleCr.json"
    sample = Path(sys.argv[1]) if len(sys.argv) > 1 else default

    print(f"\nCarvest: running competitive comparison for {sample}\n")

    try:
        report = run_comparison(sample)
        print("=== CARVEST COMPARISON REPORT ===")
        print(report)
        print("=================================\n")
    except Exception as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc
