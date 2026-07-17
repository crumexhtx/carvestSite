"""Deterministic listing deal evaluator: fair price, loan payment, insurance range."""

from __future__ import annotations

from typing import Any, Optional

from app_ai_core import verify_vehicle_exists
from feature_flags import monetization_enabled
from fetch_marketcheck import MarketCheckError, predict_market_price
from fetch_recalls import get_live_recalls, recalls_available
from vin_decode import VinDecodeError, decode_vin


CREDIT_TIERS = {
    "excellent": {"label": "Excellent (720+)", "apr_percent": 6.49},
    "good": {"label": "Good (680–719)", "apr_percent": 9.49},
    "fair": {"label": "Fair (620–679)", "apr_percent": 14.49},
    "poor": {"label": "Building credit (<620)", "apr_percent": 19.99},
}

AGE_BANDS = {
    "18-24": {"label": "18–24", "multiplier": 1.45},
    "25-34": {"label": "25–34", "multiplier": 1.15},
    "35-54": {"label": "35–54", "multiplier": 1.0},
    "55+": {"label": "55+", "multiplier": 0.95},
}

ALLOWED_TERMS = {36, 48, 60, 72}


class ListingDealError(Exception):
    pass


def _deal_signal(listing_price: float, fair_price: float) -> str:
    delta = listing_price - fair_price
    if delta <= -1500:
        return "LIKELY_GOOD_DEAL"
    if delta >= 1500:
        return "LIKELY_OVERPRICED"
    return "NEAR_MARKET"


def monthly_loan_payment(principal: float, apr_percent: float, term_months: int) -> float:
    if principal <= 0:
        return 0.0
    if term_months <= 0:
        raise ListingDealError("Loan term must be positive.")
    monthly_rate = (apr_percent / 100.0) / 12.0
    if monthly_rate == 0:
        return round(principal / term_months, 2)
    payment = principal * (
        monthly_rate * (1 + monthly_rate) ** term_months
    ) / ((1 + monthly_rate) ** term_months - 1)
    return round(payment, 2)


def estimate_insurance_range(
    *,
    listing_price: float,
    age_band: str,
    zip_code: str,
) -> dict[str, Any]:
    band = AGE_BANDS.get(age_band, AGE_BANDS["35-54"])
    # Simple illustrative model: base on vehicle price, age band, and ZIP region.
    # Not a quote — for education only.
    base_annual = 900 + (listing_price * 0.018)
    zip_prefix = zip_code[:1] if zip_code else "0"
    region_factor = {
        "0": 1.05,
        "1": 1.12,
        "2": 1.08,
        "3": 1.06,
        "4": 0.98,
        "5": 0.95,
        "6": 0.97,
        "7": 1.02,
        "8": 1.1,
        "9": 1.18,
    }.get(zip_prefix, 1.05)
    annual_mid = base_annual * band["multiplier"] * region_factor
    annual_low = annual_mid * 0.82
    annual_high = annual_mid * 1.28
    return {
        "age_band": age_band,
        "age_band_label": band["label"],
        "monthly_low": round(annual_low / 12, 2),
        "monthly_mid": round(annual_mid / 12, 2),
        "monthly_high": round(annual_high / 12, 2),
        "annual_mid": round(annual_mid, 2),
        "disclaimer": (
            "Insurance figures are educational ranges only. Real premiums depend on "
            "driving record, coverage limits, deductible, credit (where allowed), "
            "claims history, and insurer underwriting."
        ),
    }


def evaluate_listing_deal(
    *,
    vin: str,
    listing_price: float,
    mileage: int,
    zip_code: str,
    down_payment: float = 0,
    loan_term_months: int = 60,
    credit_tier: str = "good",
    age_band: str = "35-54",
    listing_url: Optional[str] = None,
) -> dict[str, Any]:
    if listing_price <= 0:
        raise ListingDealError("Listing price must be greater than zero.")
    if mileage < 0:
        raise ListingDealError("Mileage cannot be negative.")
    if not zip_code or len(str(zip_code)) != 5 or not str(zip_code).isdigit():
        raise ListingDealError("Enter a valid five-digit ZIP code.")
    if down_payment < 0:
        raise ListingDealError("Down payment cannot be negative.")
    if down_payment >= listing_price:
        raise ListingDealError("Down payment must be less than the listing price.")
    if loan_term_months not in ALLOWED_TERMS:
        raise ListingDealError("Choose a loan term of 36, 48, 60, or 72 months.")
    if credit_tier not in CREDIT_TIERS:
        raise ListingDealError("Choose a valid credit tier.")
    if age_band not in AGE_BANDS:
        raise ListingDealError("Choose a valid age band.")
    if listing_url and not listing_url.startswith(("http://", "https://")):
        raise ListingDealError("Listing URL must begin with http:// or https://.")

    try:
        vehicle = decode_vin(vin)
    except VinDecodeError as exc:
        raise ListingDealError(str(exc)) from exc

    is_valid, _, canonical_make, canonical_model = verify_vehicle_exists(
        vehicle["make"],
        vehicle["year"],
        vehicle["model"],
    )
    if is_valid and canonical_make and canonical_model:
        vehicle["make"] = canonical_make
        vehicle["model"] = canonical_model
    vehicle["catalog_verified"] = bool(is_valid)

    price_analysis: Optional[dict[str, Any]] = None
    market_note = "Market fair-price estimate unavailable."
    try:
        prediction = predict_market_price(
            vin=vehicle["vin"],
            miles=int(mileage),
            zip_code=str(zip_code),
        )
        fair_price = prediction.get("predicted_price")
        if fair_price is not None:
            fair = float(fair_price)
            delta = round(float(listing_price) - fair, 2)
            price_analysis = {
                "predicted_fair_price": fair,
                "listing_price": float(listing_price),
                "price_delta": delta,
                "deal_signal": _deal_signal(float(listing_price), fair),
            }
            market_note = "Fair price estimated from MarketCheck for this VIN, mileage, and ZIP."
    except MarketCheckError as exc:
        market_note = f"Market fair-price estimate unavailable: {exc}"

    recalls = get_live_recalls(
        vehicle["make"],
        vehicle["year"],
        vehicle["model"],
        verbose=False,
    )
    recall_lookup_ok = recalls_available(recalls)
    recall_count = (
        int(recalls.get("total_recalls_count") or 0) if recall_lookup_ok else None
    )

    amount_financed = round(float(listing_price) - float(down_payment), 2)
    selected_tier = CREDIT_TIERS[credit_tier]
    selected_payment = monthly_loan_payment(
        amount_financed,
        selected_tier["apr_percent"],
        loan_term_months,
    )

    loan_scenarios = []
    for tier_key, tier in CREDIT_TIERS.items():
        payment = monthly_loan_payment(
            amount_financed,
            tier["apr_percent"],
            loan_term_months,
        )
        loan_scenarios.append(
            {
                "credit_tier": tier_key,
                "label": tier["label"],
                "apr_percent": tier["apr_percent"],
                "monthly_payment": payment,
                "selected": tier_key == credit_tier,
            }
        )

    insurance = estimate_insurance_range(
        listing_price=float(listing_price),
        age_band=age_band,
        zip_code=str(zip_code),
    )

    ownership = {
        "loan_monthly": selected_payment,
        "insurance_monthly_low": insurance["monthly_low"],
        "insurance_monthly_mid": insurance["monthly_mid"],
        "insurance_monthly_high": insurance["monthly_high"],
        "estimated_monthly_low": round(selected_payment + insurance["monthly_low"], 2),
        "estimated_monthly_mid": round(selected_payment + insurance["monthly_mid"], 2),
        "estimated_monthly_high": round(selected_payment + insurance["monthly_high"], 2),
    }

    recommendation = _recommendation_copy(
        price_analysis=price_analysis,
        recall_count=recall_count,
        recalls_available_flag=recall_lookup_ok,
        ownership=ownership,
        down_payment=float(down_payment),
        listing_price=float(listing_price),
    )

    return {
        "vehicle": vehicle,
        "listing": {
            "price": float(listing_price),
            "mileage": int(mileage),
            "zip_code": str(zip_code),
            "listing_url": listing_url,
        },
        "price_analysis": price_analysis,
        "market_note": market_note,
        "recall_count": recall_count,
        "recalls_available": recall_lookup_ok,
        "loan": {
            "down_payment": float(down_payment),
            "amount_financed": amount_financed,
            "term_months": loan_term_months,
            "credit_tier": credit_tier,
            "selected_apr_percent": selected_tier["apr_percent"],
            "selected_monthly_payment": selected_payment,
            "scenarios": loan_scenarios,
            "disclaimer": (
                "APRs are illustrative national-style ranges for education, not a credit "
                "offer. Your dealer or lender will quote a personal rate."
            ),
        },
        "insurance": insurance,
        "ownership": ownership,
        "recommendation": recommendation,
        "next_steps": _next_steps(
            listing_price=float(listing_price),
            vin=vehicle["vin"],
        ),
        "disclaimer": (
            "Carvest provides educational estimates for research only. Confirm price, "
            "financing, insurance, and vehicle condition with qualified professionals "
            "before buying."
        ),
    }


def _next_steps(*, listing_price: float, vin: str) -> list[dict[str, str]]:
    steps = [
        {
            "id": "offer_sheet",
            "label": "Analyze the dealer offer sheet",
            "href": f"/offer-sheet?price={int(listing_price)}",
            "description": "Break down taxes, fees, and optional add-ons before signing.",
        }
    ]
    if monetization_enabled():
        steps.append(
            {
                "id": "vin_report",
                "label": "Unlock the full VIN buyer report",
                "href": f"/report?vin={vin}",
                "description": "Get risk analysis, inspection checklist, and negotiation scripts.",
            }
        )
    else:
        steps.append(
            {
                "id": "waitlist",
                "label": "Join the VIN report waitlist",
                "href": "/report",
                "description": (
                    "Paid deep-dive reports are coming after the soft launch. "
                    "Leave your email to get notified."
                ),
            }
        )
    return steps


def _recommendation_copy(
    *,
    price_analysis: Optional[dict[str, Any]],
    recall_count: Optional[int],
    recalls_available_flag: bool,
    ownership: dict[str, Any],
    down_payment: float,
    listing_price: float,
) -> dict[str, Any]:
    signal = (price_analysis or {}).get("deal_signal")
    if signal == "LIKELY_GOOD_DEAL":
        headline = "Asking price looks competitive versus the fair-price estimate."
        detail = (
            "Still verify condition with a pre-purchase inspection and confirm the "
            "out-the-door price before celebrating the deal."
        )
    elif signal == "LIKELY_OVERPRICED":
        headline = "Asking price looks high versus the fair-price estimate."
        detail = (
            "Ask the dealer to justify the price with condition, options, or recent "
            "reconditioning—or negotiate toward a lower out-the-door number."
        )
    elif signal == "NEAR_MARKET":
        headline = "Asking price is near the fair-price estimate."
        detail = (
            "Focus on total cost: fees, financing, insurance, and inspection findings "
            "can matter more than a small price difference."
        )
    else:
        headline = "We could not confirm a fair-price estimate for this listing."
        detail = (
            "Use the loan and insurance ranges to understand monthly cost, then verify "
            "pricing with comps and a full VIN report."
        )

    down_pct = (down_payment / listing_price) * 100 if listing_price else 0
    tips = [
        f"Plan for roughly {ownership['estimated_monthly_mid']:,.0f}/mo "
        f"(loan + mid-range insurance estimate) before taxes and maintenance.",
        "Request a written buyer’s order and run it through the Offer Sheet Analyzer.",
    ]
    if down_pct < 10:
        tips.append(
            "A larger down payment lowers monthly cost and can improve loan approval odds."
        )
    if not recalls_available_flag:
        tips.append(
            "Model-year recall lookup was unavailable — verify open recalls for the "
            "exact VIN with NHTSA or a franchised dealer before buying."
        )
    elif recall_count:
        tips.append(
            f"This model year shows {recall_count} recall campaign"
            f"{'' if recall_count == 1 else 's'}—confirm open recalls for the exact VIN."
        )
    else:
        tips.append(
            "No model-year recall campaigns were returned; still verify the exact VIN "
            "with NHTSA or a franchised dealer."
        )

    return {
        "headline": headline,
        "detail": detail,
        "tips": tips,
        "deal_signal": signal,
    }
