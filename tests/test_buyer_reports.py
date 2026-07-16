import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import buyer_report_service
from report_store import create_report, get_authorized_report, update_report
from vin_decode import VinDecodeError, normalize_vin


class BuyerReportStoreTests(unittest.TestCase):
    def test_vin_normalization(self) -> None:
        self.assertEqual(
            normalize_vin("1hgcm82633a004352"),
            "1HGCM82633A004352",
        )
        with self.assertRaises(VinDecodeError):
            normalize_vin("not-a-vin")

    def test_report_token_protects_persisted_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(
                os.environ,
                {
                    "REPORT_STORE_BACKEND": "sqlite",
                    "REPORT_SQLITE_PATH": str(Path(directory) / "reports.sqlite3"),
                    "REPORT_ACCESS_SECRET": "unit-test-secret",
                },
            ):
                record, token = create_report(
                    vin="1HGCM82633A004352",
                    email="buyer@example.com",
                    request_data={"vin": "1HGCM82633A004352"},
                    preview={"summary": "Preview"},
                )
                self.assertIsNone(get_authorized_report(record["id"], "wrong-token"))
                authorized = get_authorized_report(record["id"], token)
                self.assertIsNotNone(authorized)
                self.assertEqual(authorized["preview_json"]["summary"], "Preview")

                updated = update_report(
                    record["id"],
                    status="ready",
                    full_json={"markdown_report": "Complete"},
                )
                self.assertEqual(updated["status"], "ready")
                self.assertEqual(updated["full_json"]["markdown_report"], "Complete")

    def test_paid_report_builds_price_and_inspection_sections(self) -> None:
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
                    email=None,
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
                recalls = {
                    "total_recalls_count": 1,
                    "recalls_list": [{"Component": "AIR BAGS"}],
                }
                negotiation = {
                    "summary": "Use the market delta.",
                    "opening_offer": 7500,
                    "target_price": 8000,
                    "walk_away_price": 8500,
                    "talking_points": [],
                    "email_script": "Email",
                    "text_script": "Text",
                }
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
                        return_value=negotiation,
                    ),
                    patch.object(
                        buyer_report_service,
                        "get_live_recalls",
                        return_value=recalls,
                    ),
                    patch.object(buyer_report_service, "send_report_ready_email"),
                ):
                    result = buyer_report_service.build_full_report(record["id"])

                self.assertEqual(result["status"], "ready")
                self.assertEqual(
                    result["full_json"]["price_analysis"]["deal_signal"],
                    "LIKELY_OVERPRICED",
                )
                self.assertIn(
                    "AIR BAGS",
                    " ".join(result["full_json"]["inspection_checklist"]),
                )


if __name__ == "__main__":
    unittest.main()
