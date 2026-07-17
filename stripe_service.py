import os
from typing import Any
from urllib.parse import quote

import stripe

from buyer_report_service import REPORT_PRICE_CENTS
from report_store import get_authorized_report


class PaymentConfigurationError(Exception):
    pass


def development_unlock_enabled() -> bool:
    configured = os.environ.get("REPORT_DEV_UNLOCK")
    if configured is not None:
        return configured.strip().lower() in {"1", "true", "yes"}
    return os.environ.get("ENVIRONMENT", "development").lower() != "production"


def stripe_configured() -> bool:
    return bool(os.environ.get("STRIPE_SECRET_KEY", "").strip())


def create_checkout_session(report_id: str, token: str) -> dict[str, Any]:
    record = get_authorized_report(report_id, token)
    if not record:
        raise PaymentConfigurationError("Invalid report access token.")

    secret_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not secret_key:
        raise PaymentConfigurationError("Stripe is not configured.")
    stripe.api_key = secret_key

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    price_id = os.environ.get("STRIPE_PRICE_ID", "").strip()
    line_item: dict[str, Any]
    if price_id:
        line_item = {"price": price_id, "quantity": 1}
    else:
        line_item = {
            "price_data": {
                "currency": "usd",
                "unit_amount": REPORT_PRICE_CENTS,
                "product_data": {
                    "name": "Carvest Complete Buyer Report",
                    "description": "VIN-specific reliability, pricing, recall, and negotiation report.",
                },
            },
            "quantity": 1,
        }

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[line_item],
        customer_email=record.get("email") or None,
        metadata={"report_id": report_id},
        # Stripe redirects drop URL fragments, so the token must stay in the query
        # for checkout return. The report page immediately moves it to sessionStorage
        # and strips it from the address bar.
        success_url=(
            f"{frontend_url}/report/{report_id}?token={quote(token)}"
            "&checkout=success&session_id={CHECKOUT_SESSION_ID}"
        ),
        cancel_url=f"{frontend_url}/report?checkout=cancelled",
    )
    return {
        "checkout_url": session.url,
        "session_id": session.id,
        "development_unlocked": False,
    }


def construct_webhook_event(payload: bytes, signature: str) -> Any:
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        raise PaymentConfigurationError("STRIPE_WEBHOOK_SECRET is not configured.")
    return stripe.Webhook.construct_event(payload, signature, webhook_secret)


def validate_checkout_session_for_report(
    session: dict[str, Any],
    record: dict[str, Any],
) -> None:
    """Reject webhook unlocks that do not match the stored report checkout."""
    payment_status = str(session.get("payment_status") or "").strip().lower()
    if payment_status != "paid":
        raise PaymentConfigurationError(
            f"Stripe session is not paid (status={payment_status or 'unknown'})."
        )

    session_id = str(session.get("id") or "").strip()
    if not session_id:
        raise PaymentConfigurationError("Stripe session is missing an id.")

    stored_session = str(record.get("stripe_session_id") or "").strip()
    if stored_session and stored_session != session_id:
        raise PaymentConfigurationError("Stripe session does not match this report.")

    currency = str(session.get("currency") or "").strip().lower()
    if currency and currency != "usd":
        raise PaymentConfigurationError(f"Unexpected Stripe currency: {currency}.")

    # When Checkout uses ad-hoc price_data, amount must match the configured report price.
    # When STRIPE_PRICE_ID is set, trust that catalog price and skip amount matching.
    price_id = os.environ.get("STRIPE_PRICE_ID", "").strip()
    amount_total = session.get("amount_total")
    if not price_id and amount_total is not None:
        if int(amount_total) != int(REPORT_PRICE_CENTS):
            raise PaymentConfigurationError(
                f"Unexpected Stripe amount: {amount_total} (expected {REPORT_PRICE_CENTS})."
            )
