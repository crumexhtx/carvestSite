import re
from typing import Any, Optional


CATEGORIES = (
    "government_charge",
    "dealer_fee",
    "optional_product",
    "price_adjustment",
    "unknown",
)

GOVERNMENT_PATTERNS = (
    "tax",
    "sales tax",
    "state tax",
    "local tax",
    "county tax",
    "title fee",
    "registration fee",
    "license fee",
    "tag fee",
    "dmv fee",
    "motor vehicle fee",
    "title",
    "registration",
    "tags",
)
DEALER_FEE_PATTERNS = (
    "doc fee",
    "documentary fee",
    "documentation fee",
    "processing fee",
    "administrative fee",
    "admin fee",
    "dealer service fee",
    "dealer prep",
    "preparation fee",
    "reconditioning fee",
    "delivery fee",
    "transport fee",
    "handling fee",
    "inspection fee",
    "certification fee",
    "advertising fee",
    "inventory fee",
    "lot fee",
    "electronic filing fee",
)
OPTIONAL_PRODUCT_PATTERNS = (
    "gap",
    "extended warranty",
    "service contract",
    "vehicle service contract",
    "vsc",
    "maintenance plan",
    "prepaid maintenance",
    "tire and wheel",
    "tire & wheel",
    "nitrogen",
    "etch",
    "etching",
    "vin etch",
    "vin engraving",
    "theft protection",
    "anti theft",
    "paint protection",
    "fabric protection",
    "ceramic coating",
    "appearance package",
    "protection package",
    "key replacement",
    "dent protection",
    "windshield protection",
    "road hazard",
    "credit life",
    "window tint",
    "tint",
    "lojack",
    "gps tracker",
    "wheel locks",
    "floor mats",
    "mud guards",
    "door edge guards",
    "pinstripe",
    "alarm",
    "dealer installed option",
)
ADJUSTMENT_PATTERNS = (
    "market adjustment",
    "price adjustment",
    "dealer adjustment",
    "additional dealer markup",
    "adm",
    "discount",
    "rebate",
    "incentive",
    "credit",
    "allowance",
)


class OfferSheetError(Exception):
    pass


def _normalize_label(label: str) -> str:
    return re.sub(r"[^a-z0-9&]+", " ", label.lower()).strip()


def _contains_pattern(normalized: str, patterns: tuple[str, ...]) -> bool:
    padded = f" {normalized} "
    return any(f" {pattern} " in padded for pattern in patterns)


def classify_line_item(
    *,
    index: int,
    label: str,
    amount: float,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    cleaned_label = str(label).strip()
    if not cleaned_label:
        raise OfferSheetError("Each line item needs a label.")
    normalized = _normalize_label(cleaned_label)

    if _contains_pattern(normalized, GOVERNMENT_PATTERNS):
        category = "government_charge"
        rationale = (
            "The label resembles a tax, title, registration, or licensing charge. "
            "Confirm the amount with your state or local motor-vehicle agency."
        )
        review_recommended = False
        confidence = "high"
    elif _contains_pattern(normalized, OPTIONAL_PRODUCT_PATTERNS):
        category = "optional_product"
        rationale = (
            "The label resembles a protection product, service contract, or dealer add-on. "
            "Ask whether it can be declined and request its separate terms."
        )
        review_recommended = amount > 0
        confidence = "high"
    elif _contains_pattern(normalized, DEALER_FEE_PATTERNS):
        category = "dealer_fee"
        rationale = (
            "The label resembles a dealer-imposed documentation, processing, preparation, "
            "or reconditioning charge. Rules and negotiability vary by location."
        )
        review_recommended = amount > 0
        confidence = "high"
    elif _contains_pattern(normalized, ADJUSTMENT_PATTERNS):
        category = "price_adjustment"
        if amount > 0:
            rationale = (
                "This appears to increase the vehicle price. Ask why it is separate from "
                "the advertised price and whether it can be removed."
            )
            review_recommended = True
        else:
            rationale = (
                "This appears to reduce the amount due. Confirm all eligibility conditions "
                "and that the credit remains in the final contract."
            )
            review_recommended = False
        confidence = "high"
    else:
        category = "unknown"
        rationale = (
            "The label is not specific enough for reliable classification. Request a written "
            "description and ask whether the charge is mandatory."
        )
        review_recommended = amount > 0
        confidence = "low"

    return {
        "index": index,
        "label": cleaned_label,
        "amount": round(float(amount), 2),
        "notes": str(notes).strip() if notes else None,
        "category": category,
        "confidence": confidence,
        "rationale": rationale,
        "review_recommended": review_recommended,
    }


def _question_for(item: dict[str, Any]) -> Optional[dict[str, Any]]:
    label = item["label"]
    category = item["category"]
    if category == "government_charge":
        return {
            "related_labels": [label],
            "question": (
                f"Which government rate or published schedule was used to calculate "
                f"“{label}”?"
            ),
            "context": "Taxes and registration charges should be independently verifiable.",
        }
    if category == "optional_product":
        return {
            "related_labels": [label],
            "question": (
                f"Is “{label}” required to buy or finance this vehicle, or may I decline it?"
            ),
            "context": "Request the separate contract, coverage, exclusions, and cancellation terms.",
        }
    if category == "dealer_fee":
        return {
            "related_labels": [label],
            "question": (
                f"What specific service does “{label}” cover, and can the vehicle price "
                f"be adjusted to offset it?"
            ),
            "context": "Dealer-fee rules and negotiability vary by state and transaction.",
        }
    if category == "price_adjustment" and item["amount"] > 0:
        return {
            "related_labels": [label],
            "question": (
                f"Why is “{label}” added above the advertised price, and can it be removed?"
            ),
            "context": "Ask for a revised buyer’s order showing the complete price in writing.",
        }
    if category == "unknown":
        return {
            "related_labels": [label],
            "question": (
                f"What does “{label}” include, who receives the money, and is it mandatory?"
            ),
            "context": "Do not sign until every line item has a clear written explanation.",
        }
    return None


def analyze_offer_sheet(
    *,
    advertised_price: float,
    line_items: list[dict[str, Any]],
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
) -> dict[str, Any]:
    if advertised_price <= 0:
        raise OfferSheetError("Advertised price must be greater than zero.")
    if not line_items:
        raise OfferSheetError("Add at least one line item from the dealer quote.")
    if len(line_items) > 50:
        raise OfferSheetError("Offer sheets are limited to 50 line items.")

    classified = [
        classify_line_item(
            index=index,
            label=item.get("label", ""),
            amount=float(item.get("amount", 0)),
            notes=item.get("notes"),
        )
        for index, item in enumerate(line_items)
    ]
    by_category = {category: 0.0 for category in CATEGORIES}
    for item in classified:
        by_category[item["category"]] += item["amount"]
    by_category = {
        category: round(amount, 2) for category, amount in by_category.items()
    }

    line_items_subtotal = round(sum(item["amount"] for item in classified), 2)
    potential_review_amount = round(
        sum(
            item["amount"]
            for item in classified
            if item["review_recommended"] and item["amount"] > 0
        ),
        2,
    )
    out_the_door_total = round(float(advertised_price) + line_items_subtotal, 2)
    positive_total = max(float(advertised_price), 1)
    review_ratio = potential_review_amount / positive_total
    unknown_count = sum(item["category"] == "unknown" for item in classified)
    if review_ratio >= 0.08 or unknown_count >= 3:
        review_level = "high"
    elif review_ratio >= 0.02 or unknown_count:
        review_level = "moderate"
    else:
        review_level = "low"

    questions = [
        question
        for item in classified
        if (question := _question_for(item)) is not None
    ]
    return {
        "classified_items": classified,
        "totals": {
            "advertised_price": round(float(advertised_price), 2),
            "line_items_subtotal": line_items_subtotal,
            "out_the_door_total": out_the_door_total,
            "potential_review_amount": potential_review_amount,
            "by_category": by_category,
        },
        "review_level": review_level,
        "questions": questions[:20],
        "location": {
            "state": state.strip().upper() if state else None,
            "zip_code": zip_code.strip() if zip_code else None,
        },
        "disclaimer": (
            "Carvest classifies only the line items entered and does not determine whether "
            "a charge is lawful or required in your location. Confirm taxes and government "
            "fees with the appropriate agency, and review the final contract before signing."
        ),
    }
