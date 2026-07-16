import os
import time
from typing import Any, Optional
from urllib.parse import quote

from app_ai_core import generate_ai_vehicle_report, verify_vehicle_exists
from email_service import send_report_ready_email
from fetch_marketcheck import MarketCheckError, predict_market_price
from fetch_recalls import get_live_recalls
from negotiation import generate_negotiation_pack
from report_store import (
    access_token_for,
    create_report,
    get_authorized_report,
    get_report,
    update_report,
)
from vin_decode import decode_vin


REPORT_PRICE_CENTS = int(os.environ.get("BUYER_REPORT_PRICE_CENTS", "1900"))


class BuyerReportError(Exception):
    pass


def _price_signal(listing_price: float, fair_price: float) -> str:
    delta = listing_price - fair_price
    if delta <= -1500:
        return "LIKELY_GOOD_DEAL"
    if delta >= 1500:
        return "LIKELY_OVERPRICED"
    return "NEAR_MARKET"


def _vehicle_name(vehicle: dict[str, Any]) -> str:
    return f"{vehicle['year']} {vehicle['make']} {vehicle['model']}"


def _inspection_checklist(recalls: dict[str, Any]) -> list[str]:
    components = []
    for row in recalls.get("recalls_list") or []:
        component = str(row.get("Component") or "").strip()
        if component and component not in components:
            components.append(component)
    checklist = [
        "Run an exact-VIN open-recall check with NHTSA or a franchised dealer.",
        "Arrange an independent pre-purchase inspection before leaving a deposit.",
        "Cold-start the vehicle and scan all modules for current and pending trouble codes.",
        "Verify title status, ownership history, odometer consistency, and service records.",
        "Measure tire tread and brake wear, and inspect underneath for leaks or collision repairs.",
    ]
    if components:
        checklist.insert(
            1,
            f"Ask the inspector to focus on recalled systems: {', '.join(components[:3])}.",
        )
    return checklist


def create_preview(
    *,
    vin: str,
    listing_price: Optional[float] = None,
    mileage: Optional[int] = None,
    zip_code: Optional[str] = None,
    email: Optional[str] = None,
    listing_url: Optional[str] = None,
) -> dict[str, Any]:
    vehicle = decode_vin(vin)
    is_valid, _, canonical_model = verify_vehicle_exists(
        vehicle["make"],
        vehicle["year"],
        vehicle["model"],
    )
    if is_valid and canonical_model:
        vehicle["model"] = canonical_model
    vehicle["catalog_verified"] = bool(is_valid)

    recalls = get_live_recalls(
        vehicle["make"],
        vehicle["year"],
        vehicle["model"],
        verbose=False,
    )
    recall_rows = recalls.get("recalls_list") or []
    recall_count = int(recalls.get("total_recalls_count") or 0)
    top_component = recall_rows[0].get("Component") if recall_rows else None

    request_data = {
        "vin": vehicle["vin"],
        "listing_price": listing_price,
        "mileage": mileage,
        "zip_code": zip_code,
        "email": email,
        "listing_url": listing_url,
        "vehicle": vehicle,
    }
    preview = {
        "vehicle": vehicle,
        "listing_price": listing_price,
        "mileage": mileage,
        "zip_code": zip_code,
        "recall_count": recall_count,
        "top_recall_component": top_component,
        "summary": (
            f"NHTSA decoded this VIN as a {_vehicle_name(vehicle)}. "
            + (
                f"It has {recall_count} recorded recall campaign"
                f"{'' if recall_count == 1 else 's'} for this model year."
                if recall_count
                else "No recall campaigns were returned for this model year."
            )
        ),
        "visible_sections": [
            "VIN identity",
            "Model-year recall count",
            "Basic listing details",
        ],
        "locked_sections": [
            "Fair-price analysis",
            "Complete reliability and risk report",
            "Inspection checklist",
            "Negotiation targets and dealer scripts",
        ],
        "report_price_cents": REPORT_PRICE_CENTS,
    }
    record, access_token = create_report(
        vin=vehicle["vin"],
        email=email,
        request_data=request_data,
        preview=preview,
    )
    return {
        "report_id": record["id"],
        "access_token": access_token,
        "status": record["status"],
        "preview": preview,
        "report_price_cents": REPORT_PRICE_CENTS,
    }


def _build_price_analysis(request_data: dict[str, Any]) -> Optional[dict[str, Any]]:
    vin = request_data.get("vin")
    mileage = request_data.get("mileage")
    zip_code = request_data.get("zip_code")
    listing_price = request_data.get("listing_price")
    if not (vin and mileage is not None and zip_code):
        return None
    try:
        prediction = predict_market_price(
            vin=str(vin),
            miles=int(mileage),
            zip_code=str(zip_code),
        )
    except MarketCheckError:
        return None

    fair_price = prediction.get("predicted_price")
    if fair_price is None:
        return None
    analysis = {
        "predicted_fair_price": float(fair_price),
        "listing_price": float(listing_price) if listing_price is not None else None,
        "price_delta": None,
        "deal_signal": None,
    }
    if listing_price is not None:
        analysis["price_delta"] = round(float(listing_price) - float(fair_price), 2)
        analysis["deal_signal"] = _price_signal(float(listing_price), float(fair_price))
    return analysis


def build_full_report(report_id: str) -> dict[str, Any]:
    record = get_report(report_id)
    if not record:
        raise BuyerReportError("Report not found.")
    if record["status"] not in {"paid", "generating", "failed"}:
        raise BuyerReportError("Payment is required before generating this report.")

    update_report(report_id, status="generating")
    request_data = record["request_json"]
    vehicle = request_data["vehicle"]
    try:
        price_analysis = _build_price_analysis(request_data)
        profile = {
            **request_data,
            "make": vehicle["make"],
            "model": vehicle["model"],
            "year": vehicle["year"],
            "price_analysis": price_analysis,
        }
        markdown_report = generate_ai_vehicle_report(
            make=vehicle["make"],
            year=int(vehicle["year"]),
            model=vehicle["model"],
            zip_code=request_data.get("zip_code"),
            vehicle_profile=profile,
        )
        if markdown_report.startswith(("Error:", "Failed to connect")):
            raise BuyerReportError(markdown_report)

        negotiation_pack = None
        if request_data.get("listing_price") is not None:
            negotiation_input = {
                "heading": _vehicle_name(vehicle),
                "price": float(request_data["listing_price"]),
                "listing_price": float(request_data["listing_price"]),
                "miles": request_data.get("mileage"),
                "vin": request_data["vin"],
                "zip_code": request_data.get("zip_code"),
                "make": vehicle["make"],
                "model": vehicle["model"],
                "year": vehicle["year"],
                "price_analysis": price_analysis,
            }
            negotiation_pack = generate_negotiation_pack(negotiation_input)

        recalls = get_live_recalls(
            vehicle["make"],
            vehicle["year"],
            vehicle["model"],
            verbose=False,
        )
        full_report = {
            "vehicle": vehicle,
            "request": request_data,
            "markdown_report": markdown_report,
            "price_analysis": price_analysis,
            "recalls": recalls,
            "inspection_checklist": _inspection_checklist(recalls),
            "negotiation_pack": negotiation_pack,
            "generated_at": time.time(),
        }
        updated = update_report(report_id, status="ready", full_json=full_report)

        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
        token = access_token_for(report_id)
        report_url = f"{frontend_url}/report/{report_id}?token={quote(token)}"
        send_report_ready_email(
            recipient=record.get("email"),
            vehicle_name=_vehicle_name(vehicle),
            report_url=report_url,
        )
        return updated
    except Exception as exc:
        update_report(
            report_id,
            status="failed",
            full_json={"error": str(exc)},
        )
        raise


def mark_report_paid(
    report_id: str,
    *,
    stripe_session_id: Optional[str] = None,
    stripe_payment_intent_id: Optional[str] = None,
) -> dict[str, Any]:
    return update_report(
        report_id,
        status="paid",
        stripe_session_id=stripe_session_id,
        stripe_payment_intent_id=stripe_payment_intent_id,
        paid_at=time.time(),
    )


def get_report_for_client(report_id: str, token: str) -> dict[str, Any]:
    record = get_authorized_report(report_id, token)
    if not record:
        raise BuyerReportError("Invalid or expired report link.")
    return {
        "report_id": record["id"],
        "status": record["status"],
        "preview": record["preview_json"],
        "full_report": record["full_json"] if record["status"] in {"ready", "failed"} else None,
        "report_price_cents": REPORT_PRICE_CENTS,
    }
