import unittest
from unittest.mock import patch

from listing_deal_service import (
    ListingDealError,
    estimate_insurance_range,
    evaluate_listing_deal,
    monthly_loan_payment,
)


class ListingDealTests(unittest.TestCase):
    def test_monthly_payment_matches_amortization(self) -> None:
        # $20,000 at 6% APR for 60 months ≈ $386.66
        payment = monthly_loan_payment(20000, 6.0, 60)
        self.assertAlmostEqual(payment, 386.66, places=2)

    def test_zero_principal_is_zero_payment(self) -> None:
        self.assertEqual(monthly_loan_payment(0, 9.49, 60), 0.0)

    def test_insurance_range_orders_low_mid_high(self) -> None:
        estimate = estimate_insurance_range(
            listing_price=25000,
            age_band="25-34",
            zip_code="77087",
        )
        self.assertLess(estimate["monthly_low"], estimate["monthly_mid"])
        self.assertLess(estimate["monthly_mid"], estimate["monthly_high"])

    def test_evaluate_listing_deal_builds_scenarios(self) -> None:
        vehicle = {
            "vin": "1HGCM82633A004352",
            "make": "Honda",
            "model": "Accord",
            "year": 2003,
            "trim": "EX-V6",
        }
        with (
            patch("listing_deal_service.decode_vin", return_value=vehicle),
            patch(
                "listing_deal_service.verify_vehicle_exists",
                return_value=(True, "ok", "Accord"),
            ),
            patch(
                "listing_deal_service.predict_market_price",
                return_value={"predicted_price": 9000},
            ),
            patch(
                "listing_deal_service.get_live_recalls",
                return_value={"total_recalls_count": 2, "recalls_list": []},
            ),
        ):
            result = evaluate_listing_deal(
                vin=vehicle["vin"],
                listing_price=10500,
                mileage=120000,
                zip_code="77087",
                down_payment=2000,
                loan_term_months=60,
                credit_tier="good",
                age_band="35-54",
                listing_url="https://dealer.example/car",
            )

        self.assertEqual(result["price_analysis"]["deal_signal"], "LIKELY_OVERPRICED")
        self.assertEqual(result["loan"]["amount_financed"], 8500)
        self.assertEqual(len(result["loan"]["scenarios"]), 4)
        self.assertTrue(any(s["selected"] for s in result["loan"]["scenarios"]))
        self.assertGreater(result["ownership"]["estimated_monthly_mid"], 0)
        self.assertEqual(len(result["next_steps"]), 2)

    def test_rejects_invalid_term(self) -> None:
        with self.assertRaises(ListingDealError):
            evaluate_listing_deal(
                vin="1HGCM82633A004352",
                listing_price=10000,
                mileage=50000,
                zip_code="77087",
                loan_term_months=50,
            )


if __name__ == "__main__":
    unittest.main()
