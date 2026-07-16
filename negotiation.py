import json
from typing import Any, Optional

from app_ai_core import verify_vehicle_exists
from fetch_marketcheck import MarketCheckError, predict_market_price
from fetch_recalls import get_live_recalls
from openai_client import create_openai_client

client = create_openai_client()


def _compute_offers(listing_price: float, fair_price: Optional[float]) -> dict[str, Optional[float]]:
    if fair_price is None:
        return {
            "opening_offer": round(listing_price * 0.95, 2),
            "walk_away_price": round(listing_price * 1.02, 2),
            "target_price": round(listing_price * 0.97, 2),
        }

    delta = listing_price - fair_price
    if delta >= 1500:
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

    return {
        "opening_offer": round(max(opening, listing_price * 0.85), 2),
        "target_price": round(target, 2),
        "walk_away_price": round(walk_away, 2),
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

    recall_context = {"total_recalls_count": 0, "top_components": []}
    if make and model and year:
        is_valid, _, canonical = verify_vehicle_exists(make, int(year), model)
        if is_valid:
            recalls = get_live_recalls(make, int(year), canonical)
            recall_context = {
                "total_recalls_count": recalls.get("total_recalls_count", 0),
                "top_components": [
                    item.get("Component")
                    for item in recalls.get("recalls_list", [])[:3]
                    if item.get("Component")
                ],
            }

    offers = _compute_offers(price, fair_price)

    system_prompt = """
You are Carvest, an automotive buyer negotiation coach.

Generate practical, polite negotiation guidance for a used-car shopper.
Use only the provided listing and market facts. Do not invent recall counts or prices.

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
    raw.setdefault("opening_offer", offers["opening_offer"])
    raw.setdefault("target_price", offers["target_price"])
    raw.setdefault("walk_away_price", offers["walk_away_price"])
    raw["price_analysis"] = price_analysis
    return raw
