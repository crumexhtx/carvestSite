import json
import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import env_setup  # noqa: F401
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from app_ai_core import generate_ai_vehicle_report, verify_vehicle_exists
from buyer_report_service import (
    BuyerReportError,
    build_full_report,
    create_preview,
    get_report_for_client,
    mark_report_paid,
)
from compare_vehicles import build_comparison_dataset, generate_comparison_report
from fetch_marketcheck import MarketCheckError, get_market_snapshot, search_by_criteria
from home_insights import get_home_insights
from inventory_stats import get_inventory_scale
from feature_flags import monetization_enabled, public_feature_flags, waitlist_enabled
from feedback_store import FeedbackError, submit_feedback
from listing_deal_service import ListingDealError, evaluate_listing_deal
from negotiation import generate_negotiation_pack
from offer_sheet_service import OfferSheetError, analyze_offer_sheet
from rate_limit import ApiRateLimitMiddleware
from report_store import ReportStoreError, get_report, update_report
from stripe_service import (
    PaymentConfigurationError,
    construct_webhook_event,
    create_checkout_session,
    development_unlock_enabled,
    stripe_configured,
    validate_checkout_session_for_report,
)
from vehicle_assistant import process_assistant_turn
from vehicle_reference_image import fetch_reference_image_bytes, resolve_vehicle_photo
from vin_decode import VinDecodeError
from waitlist_store import WaitlistError, add_waitlist_email

VEHICLES_FILE = Path(__file__).parent / "vehicles.json"
LOCAL_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]


def _allowed_origins() -> list[str]:
    configured = os.environ.get("ALLOWED_ORIGINS", "")
    origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    return origins or LOCAL_ORIGINS


app = FastAPI(title="Carvest API", version="0.1.0")
app.add_middleware(ApiRateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class VehicleQuery(BaseModel):
    make: str = ""
    year: str = ""
    model: str = ""
    zip_code: Optional[str] = None
    trim: Optional[str] = None


class AssistantChatRequest(BaseModel):
    message: str
    criteria: Optional[dict] = None
    history: Optional[list[dict[str, str]]] = None


class CriteriaSearchRequest(BaseModel):
    criteria: dict
    start: int = 0
    rows: int = 24


class NegotiationRequest(BaseModel):
    heading: str
    price: float
    miles: Optional[int] = None
    vin: Optional[str] = None
    zip_code: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    dom: Optional[int] = None
    dealer_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    deal_signal: Optional[str] = None
    predicted_fair_price: Optional[float] = None
    listing_price: Optional[float] = None
    price_delta: Optional[float] = None


class BuyerReportPreviewRequest(BaseModel):
    vin: str
    listing_price: Optional[float] = None
    mileage: Optional[int] = None
    zip_code: Optional[str] = None
    email: Optional[str] = None
    listing_url: Optional[str] = None


class BuyerReportCheckoutRequest(BaseModel):
    access_token: str


class OfferSheetLineItem(BaseModel):
    label: str
    amount: float
    notes: Optional[str] = None


class OfferSheetAnalyzeRequest(BaseModel):
    advertised_price: float
    line_items: list[OfferSheetLineItem]
    state: Optional[str] = None
    zip_code: Optional[str] = None


class ListingDealRequest(BaseModel):
    vin: str
    listing_price: float
    mileage: int
    zip_code: str
    down_payment: float = 0
    loan_term_months: int = 60
    credit_tier: str = "good"
    age_band: str = "35-54"
    listing_url: Optional[str] = None


class WaitlistRequest(BaseModel):
    email: str
    source: Optional[str] = "soft_launch"


class FeedbackRequest(BaseModel):
    message: str
    category: str = "other"
    email: Optional[str] = None
    page_path: Optional[str] = None


def _require_monetization() -> None:
    if not monetization_enabled():
        raise HTTPException(
            status_code=403,
            detail=(
                "Paid VIN reports are not available during the soft launch. "
                "Use Listing deal check and Offer analyzer for free tools."
            ),
        )


def _load_vehicle_db() -> dict:
    with open(VEHICLES_FILE, encoding="utf-8") as handle:
        return json.load(handle)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "carvest",
        "version": app.version,
        "features": public_feature_flags(),
    }


@app.get("/api/features")
def features() -> dict:
    return public_feature_flags()


@app.get("/api/vehicle-reference-image")
def vehicle_reference_image(
    make: str = Query(...),
    model: str = Query(...),
    year: Optional[int] = Query(default=None),
) -> dict:
    make = make.strip()
    model = model.strip()
    if not make or not model:
        raise HTTPException(status_code=400, detail="Make and model are required.")
    resolved = resolve_vehicle_photo(None, make, model, year)
    proxy_params = f"make={quote(make)}&model={quote(model)}"
    if year:
        proxy_params += f"&year={int(year)}"
    return {
        "make": make,
        "model": model,
        "year": year,
        "photo": resolved.get("photo"),
        "photo_source": resolved.get("photo_source"),
        # Browser-safe URL served by Carvest (avoids Wikimedia hotlink failures).
        "proxy_photo": (
            f"/api/vehicle-reference-image/file?{proxy_params}"
            if resolved.get("photo")
            else None
        ),
    }


@app.get("/api/vehicle-reference-image/file")
def vehicle_reference_image_file(
    make: str = Query(...),
    model: str = Query(...),
    year: Optional[int] = Query(default=None),
) -> Response:
    make = make.strip()
    model = model.strip()
    if not make or not model:
        raise HTTPException(status_code=400, detail="Make and model are required.")
    try:
        content, content_type = fetch_reference_image_bytes(make, model, year)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not load reference image: {exc}",
        ) from exc
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Disposition": "inline",
        },
    )


@app.get("/api/makes")
def list_makes() -> list[str]:
    return sorted(_load_vehicle_db().keys())


@app.get("/api/models")
def list_models(make: str = Query(...), year: str = Query(...)) -> list[str]:
    db = _load_vehicle_db()
    if make not in db or year not in db[make]:
        raise HTTPException(status_code=404, detail="Make or year not found.")
    return db[make][year]


@app.post("/api/search/listings")
def search_listings(payload: VehicleQuery) -> dict:
    if payload.make and payload.model and payload.year:
        is_valid, message, canonical_make, canonical_model = verify_vehicle_exists(
            payload.make, int(payload.year), payload.model
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)

        try:
            return get_market_snapshot(
                make=canonical_make,
                model=canonical_model,
                year=int(payload.year),
                zip_code=payload.zip_code,
                max_listings=12,
                max_price_predictions=4,
            )
        except MarketCheckError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    raise HTTPException(
        status_code=400,
        detail="Use /api/search/criteria for flexible searches or provide make, model, and year.",
    )


@app.post("/api/search/criteria")
def search_listings_by_criteria(payload: CriteriaSearchRequest) -> dict:
    try:
        return search_by_criteria(
            payload.criteria,
            rows=payload.rows,
            start=payload.start,
        )
    except MarketCheckError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/inventory/scale")
def inventory_scale() -> dict:
    try:
        return get_inventory_scale()
    except MarketCheckError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/negotiation")
def create_negotiation_pack(payload: NegotiationRequest) -> dict:
    try:
        listing = payload.model_dump()
        if payload.predicted_fair_price is not None:
            listing["price_analysis"] = {
                "predicted_fair_price": payload.predicted_fair_price,
                "listing_price": payload.listing_price or payload.price,
                "price_delta": payload.price_delta,
                "deal_signal": payload.deal_signal,
            }
        return generate_negotiation_pack(listing)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/listing-deal/evaluate")
def evaluate_listing(payload: ListingDealRequest) -> dict:
    try:
        return evaluate_listing_deal(**payload.model_dump())
    except ListingDealError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not evaluate this listing: {exc}",
        ) from exc


@app.post("/api/offer-sheet/analyze")
def analyze_dealer_offer(payload: OfferSheetAnalyzeRequest) -> dict:
    if payload.advertised_price <= 0 or payload.advertised_price > 10_000_000:
        raise HTTPException(status_code=400, detail="Enter a valid advertised price.")
    if not payload.line_items:
        raise HTTPException(status_code=400, detail="Add at least one dealer line item.")
    if len(payload.line_items) > 50:
        raise HTTPException(status_code=400, detail="Offer sheets are limited to 50 line items.")
    if payload.state and (len(payload.state.strip()) != 2 or not payload.state.strip().isalpha()):
        raise HTTPException(status_code=400, detail="Use a two-letter state code.")
    if payload.zip_code and (
        len(payload.zip_code.strip()) != 5 or not payload.zip_code.strip().isdigit()
    ):
        raise HTTPException(status_code=400, detail="Enter a valid five-digit ZIP code.")
    for item in payload.line_items:
        if not item.label.strip() or len(item.label.strip()) > 120:
            raise HTTPException(status_code=400, detail="Each line item needs a short label.")
        if abs(item.amount) > 10_000_000:
            raise HTTPException(status_code=400, detail="A line-item amount is outside the valid range.")
    try:
        return analyze_offer_sheet(**payload.model_dump())
    except OfferSheetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/home/insights")
def home_insights() -> dict:
    try:
        return get_home_insights()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/waitlist")
def join_waitlist(payload: WaitlistRequest) -> dict:
    if not waitlist_enabled():
        raise HTTPException(status_code=403, detail="Waitlist signup is currently closed.")
    try:
        result = add_waitlist_email(payload.email, payload.source)
        return {
            "status": "subscribed",
            "email": result["email"],
            "message": "You're on the list. We'll notify you when paid VIN reports launch.",
        }
    except WaitlistError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/feedback")
def create_feedback(payload: FeedbackRequest) -> dict:
    try:
        result = submit_feedback(**payload.model_dump())
        return {
            "status": "received",
            "id": result["id"],
            "message": "Thanks — your feedback helps shape Carvest.",
        }
    except FeedbackError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/buyer-reports/preview")
def create_buyer_report_preview(payload: BuyerReportPreviewRequest) -> dict:
    _require_monetization()
    if payload.listing_price is not None and payload.listing_price <= 0:
        raise HTTPException(status_code=400, detail="Listing price must be greater than zero.")
    if payload.mileage is not None and payload.mileage < 0:
        raise HTTPException(status_code=400, detail="Mileage cannot be negative.")
    if payload.zip_code and (len(payload.zip_code) != 5 or not payload.zip_code.isdigit()):
        raise HTTPException(status_code=400, detail="Enter a valid five-digit ZIP code.")
    if payload.email and (
        "@" not in payload.email or payload.email.startswith("@") or payload.email.endswith("@")
    ):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if payload.listing_url and not payload.listing_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Listing URL must begin with http:// or https://.")
    try:
        return create_preview(**payload.model_dump())
    except (VinDecodeError, BuyerReportError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not build report preview: {exc}") from exc


@app.get("/api/buyer-reports/{report_id}")
def get_buyer_report(
    report_id: str,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    try:
        return get_report_for_client(report_id, token)
    except BuyerReportError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.post("/api/buyer-reports/{report_id}/checkout")
def checkout_buyer_report(
    report_id: str,
    payload: BuyerReportCheckoutRequest,
) -> dict:
    _require_monetization()
    try:
        report = get_report_for_client(report_id, payload.access_token)
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
        if report["status"] == "ready":
            return {
                "checkout_url": (
                    f"{frontend_url}/report/{report_id}"
                    f"?token={quote(payload.access_token)}"
                ),
                "development_unlocked": development_unlock_enabled(),
            }

        if not stripe_configured() and development_unlock_enabled():
            mark_report_paid(report_id, stripe_session_id="development")
            build_full_report(report_id)
            return {
                "checkout_url": (
                    f"{frontend_url}/report/{report_id}"
                    f"?token={quote(payload.access_token)}&checkout=development"
                ),
                "development_unlocked": True,
            }

        checkout = create_checkout_session(report_id, payload.access_token)
        update_report(report_id, stripe_session_id=checkout.get("session_id"))
        return checkout
    except (BuyerReportError, PaymentConfigurationError, ReportStoreError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not start checkout: {exc}") from exc


@app.post("/api/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    stripe_signature: Optional[str] = Header(default=None, alias="stripe-signature"),
) -> dict[str, bool]:
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature.")
    payload = await request.body()
    try:
        event = construct_webhook_event(payload, stripe_signature)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Stripe webhook: {exc}") from exc

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        report_id = (session.get("metadata") or {}).get("report_id")
        session_id = session.get("id")
        if not report_id or not session_id:
            return {"received": True}

        record = get_report(report_id)
        if not record:
            raise HTTPException(status_code=400, detail="Unknown report for Stripe session.")

        try:
            validate_checkout_session_for_report(session, record)
        except PaymentConfigurationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if record.get("status") in {"paid", "generating", "ready"}:
            return {"received": True}

        mark_report_paid(
            report_id,
            stripe_session_id=session_id,
            stripe_payment_intent_id=session.get("payment_intent"),
        )
        background_tasks.add_task(build_full_report, report_id)
    return {"received": True}


@app.post("/api/assistant/chat")
def assistant_chat(payload: AssistantChatRequest) -> dict:
    try:
        return process_assistant_turn(
            message=payload.message,
            criteria=payload.criteria,
            history=payload.history,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/report")
def create_report(payload: VehicleQuery) -> dict[str, str]:
    if not (payload.make and payload.model and payload.year):
        raise HTTPException(
            status_code=400,
            detail="Buyer reports require make, model, and year.",
        )

    profile = payload.model_dump()
    report = generate_ai_vehicle_report(
        make=payload.make,
        year=int(payload.year),
        model=payload.model,
        zip_code=payload.zip_code,
        vehicle_profile=profile,
    )
    if report.startswith("Error:"):
        raise HTTPException(status_code=400, detail=report)
    return {"report": report}


@app.post("/api/compare")
def create_comparison(payload: VehicleQuery) -> dict:
    if not (payload.make and payload.model and payload.year):
        raise HTTPException(
            status_code=400,
            detail="Comparison requires make, model, year, and ZIP code.",
        )
    profile = payload.model_dump()
    if not payload.zip_code:
        raise HTTPException(status_code=400, detail="zip_code is required for comparison mode.")

    is_valid, message, canonical_make, canonical_model = verify_vehicle_exists(
        payload.make,
        int(payload.year),
        payload.model,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    profile["make"] = canonical_make
    profile["model"] = canonical_model

    dataset = build_comparison_dataset(profile)
    report = generate_comparison_report(profile, dataset=dataset)
    if report.startswith("Error:"):
        raise HTTPException(status_code=400, detail=report)

    return {"report": report, "dataset": dataset}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="127.0.0.1", port=8000, reload=True)
