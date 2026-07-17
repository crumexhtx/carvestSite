"""HMAC trust signatures for listing snapshots passed through the frontend."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any, Optional


class ListingTrustError(Exception):
    pass


def _secret() -> bytes:
    secret = (
        os.environ.get("LISTING_TRUST_SECRET", "").strip()
        or os.environ.get("REPORT_ACCESS_SECRET", "").strip()
    )
    if not secret:
        if os.environ.get("ENVIRONMENT", "development").lower() == "production":
            raise ListingTrustError("LISTING_TRUST_SECRET is required in production.")
        secret = "carvest-local-listing-trust-only"
    return secret.encode("utf-8")


def _canonical_number(value: Any) -> Optional[float | int]:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return number


def listing_fingerprint(listing: dict[str, Any]) -> dict[str, Any]:
    analysis = listing.get("price_analysis") or {}
    return {
        "listing_id": str(listing.get("listing_id") or listing.get("id") or "") or None,
        "vin": str(listing.get("vin") or "") or None,
        "price": _canonical_number(listing.get("price")),
        "miles": _canonical_number(listing.get("miles")),
        "vdp_url": str(listing.get("vdp_url") or "") or None,
        "predicted_fair_price": _canonical_number(analysis.get("predicted_fair_price")),
        "deal_signal": str(
            analysis.get("deal_signal") or listing.get("deal_signal") or ""
        )
        or None,
        "dealer_name": str(
            listing.get("dealer_name") or listing.get("dealer") or ""
        )
        or None,
    }


def sign_listing(listing: dict[str, Any]) -> str:
    payload = json.dumps(
        listing_fingerprint(listing),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def attach_listing_trust(listing: dict[str, Any]) -> dict[str, Any]:
    row = dict(listing)
    row["trust_sig"] = sign_listing(row)
    return row


def verify_listing_trust(
    *,
    listing_id: Optional[str] = None,
    vin: Optional[str] = None,
    price: Optional[float] = None,
    miles: Optional[float] = None,
    vdp_url: Optional[str] = None,
    predicted_fair_price: Optional[float] = None,
    deal_signal: Optional[str] = None,
    dealer_name: Optional[str] = None,
    trust_sig: Optional[str] = None,
) -> bool:
    if not trust_sig:
        return False
    candidate = {
        "listing_id": listing_id,
        "vin": vin,
        "price": price,
        "miles": miles,
        "vdp_url": vdp_url,
        "price_analysis": {
            "predicted_fair_price": predicted_fair_price,
            "deal_signal": deal_signal,
        },
        "dealer_name": dealer_name,
    }
    expected = sign_listing(candidate)
    return hmac.compare_digest(str(trust_sig), expected)
