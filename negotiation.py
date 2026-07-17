import json
import logging
from typing import Any, Optional

from app_ai_core import verify_vehicle_exists
from fetch_marketcheck import MarketCheckError, predict_market_price
from fetch_recalls import get_live_recalls, recalls_available
from openai_client import create_openai_client

client = create_openai_client()
logger = logging.getLogger(__name__)


def _compute_offers(listing_price: float, fair_price: Optional[float]) -> dict[str, Optional[float]]:
    if fair_price is None:
        opening = round(listing_price * 0.95, 2)
        target = round(listing_price * 0.97, 2)
        walk_away = round(listing_price * 1.02, 2)
        return {
            "opening_offer": opening,
            "target_price": target,
            "walk_away_price": walk_away,
        }

    delta = listing_price - fair_price
    if delta >= 1500:
        # Overpriced: anchor to fair value, never to a high fraction of asking price.
        opening = fair_price - 500
        target = fair_price
        walk_away = fair_price + 800
    elif delta <= -1500:
        opening = listing_price - 300
        target = listing_price
        walk_away = listing_price + 1200
    else:
        opening = fair_price - 250
        target = fair_price
        walk_away = fair_price + 600
        # Mild cases can keep opening from collapsing too far below asking.
        opening = max(opening, listing_price * 0.85)

    opening = min(opening, target)
    walk_away = max(walk_away, target)
    if opening <= 0:
        opening = max(target * 0.9, 1.0)

    return {
        "opening_offer": round(opening, 2),
        "target_price": round(target, 2),
        "walk_away_price": round(walk_away, 2),
    }


def _fallback_negotiation_pack(
    *,
    offers: dict[str, Optional[float]],
    price_analysis: dict[str, Any],
    deal_signal: Optional[str],
    recall_context: dict[str, Any],
) -> dict[str, Any]:
    opening = offers["opening_offer"]
    target = offers["target_price"]
    walk_away = offers["walk_away_price"]
    if deal_signal == "LIKELY_OVERPRICED":
        summary = (
            "This listing looks overpriced versus the fair-value estimate. "
            "Open below market and keep the conversation on comps and condition."
        )
    elif deal_signal == "LIKELY_GOOD_DEAL":
        summary = (
            "Pricing already looks competitive. Ask for a modest improvement on fees "
            "or extras rather than a deep discount."
        )
    else:
        summary = (
            "Use a polite, data-backed offer anchored to fair value and confirm "
            "out-the-door price before committing."
        )

    talking_points = [
        f"Open at about ${opening:,.0f} and explain that it reflects current market value.",
        f"Your target close is about ${target:,.0f}; be ready to walk near ${walk_away:,.0f}.",
    ]
    if recall_context.get("available") is False:
        talking_points.append(
            "Recall data was unavailable during this check—verify open recalls for the exact VIN before deposit."
        )
    elif recall_context.get("total_recalls_count"):
        talking_points.append(
            "Ask the dealer to document completion of any open recalls for this VIN."
        )

    return {
        "summary": summary,
        "opening_offer": opening,
        "target_price": target,
        "walk_away_price": walk_away,
        "talking_points": talking_points,
        "email_script": (
            f"Hi — thanks for the details. Based on current market value I'm prepared to "
            f"offer ${opening:,.0f}. If we can meet around ${target:,.0f} out the door, "
            f"I'm ready to move quickly after inspection."
        ),
        "text_script": (
            f"Hi — interested if we can get close to ${target:,.0f} OTD. "
            f"Happy to come by after a PPI."
        ),
        "caution": (
            "This is educational negotiation guidance only, not legal or financial advice."
        ),
        "price_analysis": price_analysis,
        "generated_by": "fallback",
    }


def generate_negotiation_pack(listing: dict[str, Any]) -> dict[str, Any]:
    heading = listing.get("heading") or "Vehicle listing"
    price = float(listing.get("price") or 0)
    miles = listing.get("miles")
    vin = listing.get("vin")
    zip_code = listing.get("zip_code") or listing.get("zip")
    make = listing.get("make")
    model = listing.get("model")
    year = listing.get("year")
    dom = listing.get("dom")
    dealer_name = listing.get("dealer_name")
    city = listing.get("city")
    state = listing.get("state")

    price_analysis = listing.get("price_analysis") or {}
    fair_price = price_analysis.get("predicted_fair_price")
    deal_signal = price_analysis.get("deal_signal")

    if fair_price is None and vin and zip_code and miles is not None:
        try:
            prediction = predict_market_price(
                vin=str(vin),
                miles=int(miles),
                zip_code=str(zip_code),
            )
            fair_price = prediction.get("predicted_price")
            if fair_price is not None and price:
                delta = round(price - fair_price, 2)
                deal_signal = (
                    "LIKELY_GOOD_DEAL"
                    if delta <= -1500
                    else "LIKELY_OVERPRICED"
                    if delta >= 1500
                    else "NEAR_MARKET"
                )
                price_analysis = {
                    "predicted_fair_price": fair_price,
                    "listing_price": price,
                    "price_delta": delta,
                    "deal_signal": deal_signal,
                }
        except MarketCheckError:
            pass

    recall_context: dict[str, Any] = {
        "available": False,
        "total_recalls_count": None,
        "top_components": [],
    }
    if make and model and year:
        is_valid, _, canonical_make, canonical_model = verify_vehicle_exists(
            make, int(year), model
        )
        if is_valid:
            recalls = get_live_recalls(canonical_make, int(year), canonical_model)
            if recalls_available(recalls):
                recall_context = {
                    "available": True,
                    "total_recalls_count": recalls.get("total_recalls_count", 0),
                    "top_components": [
                        item.get("Component")
                        for item in recalls.get("recalls_list", [])[:3]
                        if item.get("Component")
                    ],
                }
            else:
                recall_context = {
                    "available": False,
                    "total_recalls_count": None,
                    "top_components": [],
                    "error": recalls.get("error"),
                }

    offers = _compute_offers(price, fair_price)

    system_prompt = """
You are Carvest, an automotive buyer negotiation coach.

Generate practical, polite negotiation guidance for a used-car shopper.
Use only the provided listing and market facts. Do not invent recall counts or prices.
If recall data is unavailable, say so — never claim there are zero recalls.

Return ONLY valid JSON:
{
  "summary": "2-3 sentence overview of negotiation posture",
  "opening_offer": number,
  "target_price": number,
  "walk_away_price": number,
  "talking_points": ["...", "...", "..."],
  "email_script": "Full short email to dealer",
  "text_script": "Short SMS-style message",
  "caution": "One sentence disclaimer that this is guidance, not legal/financial advice"
}

Rules:
- Keep opening_offer <= target_price <= walk_away_price.
- If listing is overpriced, lean on market value, DOM, and recalls when available.
- If already a good deal, suggest smaller discount asks and focus on fees/warranty.
- Scripts should sound natural, confident, and respectful.
- Include specific dollar amounts from the offer guidance when possible.
"""

    user_payload = {
        "listing": {
            "heading": heading,
            "price": price,
            "miles": miles,
            "dom": dom,
            "dealer_name": dealer_name,
            "city": city,
            "state": state,
            "deal_signal": deal_signal,
        },
        "price_analysis": price_analysis,
        "offer_guidance": offers,
        "recall_context": recall_context,
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, indent=2)},
            ],
            temperature=0.4,
        )
        raw = json.loads(response.choices[0].message.content or "{}")
        if not isinstance(raw, dict):
            raise ValueError("Negotiation model returned non-object JSON.")
    except Exception as exc:
        logger.warning("Negotiation AI unavailable, using deterministic fallback: %s", exc)
        return _fallback_negotiation_pack(
            offers=offers,
            price_analysis=price_analysis,
            deal_signal=deal_signal,
            recall_context=recall_context,
        )

    raw.setdefault("opening_offer", offers["opening_offer"])
    raw.setdefault("target_price", offers["target_price"])
    raw.setdefault("walk_away_price", offers["walk_away_price"])

    try:
        opening = float(raw["opening_offer"])
        target = float(raw["target_price"])
        walk_away = float(raw["walk_away_price"])
        if not (opening <= target <= walk_away):
            raw["opening_offer"] = offers["opening_offer"]
            raw["target_price"] = offers["target_price"]
            raw["walk_away_price"] = offers["walk_away_price"]
        else:
            raw["opening_offer"] = round(opening, 2)
            raw["target_price"] = round(target, 2)
            raw["walk_away_price"] = round(walk_away, 2)
    except (TypeError, ValueError, KeyError):
        raw["opening_offer"] = offers["opening_offer"]
        raw["target_price"] = offers["target_price"]
        raw["walk_away_price"] = offers["walk_away_price"]

    raw["price_analysis"] = price_analysis
    return raw
