import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import buyer_report_service
import negotiation
from app_ai_core import verify_vehicle_exists
from fetch_recalls import clear_recalls_cache, get_live_recalls, recalls_available
from report_store import create_report
from stripe_service import PaymentConfigurationError, validate_checkout_session_for_report
from vin_decode import VinDecodeError, normalize_vin, vin_check_digit_valid


class VinValidationTests(unittest.TestCase):
    def test_check_digit_accepts_known_valid_vin(self) -> None:
        self.assertTrue(vin_check_digit_valid("1HGCM82633A004352"))
        self.assertEqual(normalize_vin("1hgcm82633a004352"), "1HGCM82633A004352")

    def test_check_digit_rejects_invalid_vin(self) -> None:
        self.assertFalse(vin_check_digit_valid("1HGCM82630A004352"))
        with self.assertRaises(VinDecodeError):
            normalize_vin("1HGCM82630A004352")


class CatalogMatchingTests(unittest.TestCase):
    def test_case_insensitive_make_and_model(self) -> None:
        is_valid, _, make, model = verify_vehicle_exists("gmc", 2023, "sierra")
        self.assertTrue(is_valid)
        self.assertEqual(make, "GMC")
        self.assertTrue(str(model).lower().startswith("sierra"))

    def test_rav4_case_variants(self) -> None:
        is_valid, _, make, model = verify_vehicle_exists("TOYOTA", 2020, "rav4")
        self.assertTrue(is_valid)
        self.assertEqual(make, "Toyota")
        self.assertEqual(model, "RAV4")


class RecallAvailabilityTests(unittest.TestCase):
    def tearDown(self) -> None:
        clear_recalls_cache()

    def test_request_failure_is_not_zero_recalls(self) -> None:
        class FakeResponse:
            def raise_for_status(self):
                raise __import__("requests").exceptions.Timeout("timeout")

            def json(self):
                return {}

        with patch("fetch_recalls.requests.get", return_value=FakeResponse()):
            payload = get_live_recalls(
                "Ford", 2015, "Explorer", verbose=False, use_cache=False
            )

        self.assertFalse(recalls_available(payload))
        self.assertIsNone(payload.get("total_recalls_count"))
        self.assertTrue(payload.get("error"))


class NegotiationOfferTests(unittest.TestCase):
    def test_overpriced_opening_never_exceeds_target(self) -> None:
        offers = negotiation._compute_offers(50000, 30000)
        self.assertLessEqual(offers["opening_offer"], offers["target_price"])
        self.assertLessEqual(offers["target_price"], offers["walk_away_price"])
        self.assertEqual(offers["target_price"], 30000)

    def test_ai_failure_returns_deterministic_fallback(self) -> None:
        with patch.object(
            negotiation.client.chat.completions,
            "create",
            side_effect=RuntimeError("openai down"),
        ):
            pack = negotiation.generate_negotiation_pack(
                {
                    "heading": "Test Car",
                    "price": 20000,
                    "price_analysis": {
                        "predicted_fair_price": 18000,
                        "deal_signal": "LIKELY_OVERPRICED",
                    },
                }
            )

        self.assertEqual(pack.get("generated_by"), "fallback")
        self.assertLessEqual(pack["opening_offer"], pack["target_price"])
        self.assertLessEqual(pack["target_price"], pack["walk_away_price"])


class BuyerReportEmailIsolationTests(unittest.TestCase):
    def test_email_failure_keeps_report_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(
                os.environ,
                {
                    "REPORT_STORE_BACKEND": "sqlite",
                    "REPORT_SQLITE_PATH": str(Path(directory) / "reports.sqlite3"),
                    "REPORT_ACCESS_SECRET": "unit-test-secret",
                },
            ):
                vehicle = {
                    "vin": "1HGCM82633A004352",
                    "make": "Honda",
                    "model": "Accord",
                    "year": 2003,
                }
                record, _ = create_report(
                    vin=vehicle["vin"],
                    email="buyer@example.com",
                    request_data={
                        "vin": vehicle["vin"],
                        "vehicle": vehicle,
                        "listing_price": 9000,
                        "mileage": 100000,
                        "zip_code": "77087",
                    },
                    preview={"vehicle": vehicle},
                )
                buyer_report_service.mark_report_paid(record["id"])
                with (
                    patch.object(
                        buyer_report_service,
                        "predict_market_price",
                        return_value={"predicted_price": 7000},
                    ),
                    patch.object(
                        buyer_report_service,
                        "generate_ai_vehicle_report",
                        return_value="### Report",
                    ),
                    patch.object(
                        buyer_report_service,
                        "generate_negotiation_pack",
                        return_value={"summary": "ok", "opening_offer": 6500},
                    ),
                    patch.object(
                        buyer_report_service,
                        "get_live_recalls",
                        return_value={
                            "available": True,
                            "total_recalls_count": 0,
                            "recalls_list": [],
                        },
                    ),
                    patch.object(
                        buyer_report_service,
                        "send_report_ready_email",
                        side_effect=RuntimeError("resend down"),
                    ),
                ):
                    result = buyer_report_service.build_full_report(record["id"])

                self.assertEqual(result["status"], "ready")
                self.assertEqual(result["full_json"]["markdown_report"], "### Report")


class StripeWebhookValidationTests(unittest.TestCase):
    def test_rejects_unpaid_session(self) -> None:
        with self.assertRaises(PaymentConfigurationError):
            validate_checkout_session_for_report(
                {
                    "id": "cs_test_1",
                    "payment_status": "unpaid",
                    "currency": "usd",
                    "amount_total": 1900,
                },
                {"stripe_session_id": "cs_test_1"},
            )

    def test_rejects_session_mismatch(self) -> None:
        with self.assertRaises(PaymentConfigurationError):
            validate_checkout_session_for_report(
                {
                    "id": "cs_test_other",
                    "payment_status": "paid",
                    "currency": "usd",
                    "amount_total": 1900,
                },
                {"stripe_session_id": "cs_test_1"},
            )

    def test_accepts_matching_paid_session(self) -> None:
        with patch.dict(os.environ, {"STRIPE_PRICE_ID": "", "BUYER_REPORT_PRICE_CENTS": "1900"}):
            validate_checkout_session_for_report(
                {
                    "id": "cs_test_1",
                    "payment_status": "paid",
                    "currency": "usd",
                    "amount_total": 1900,
                },
                {"stripe_session_id": "cs_test_1"},
            )


if __name__ == "__main__":
    unittest.main()
