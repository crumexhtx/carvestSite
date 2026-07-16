import unittest

from offer_sheet_service import OfferSheetError, analyze_offer_sheet


class OfferSheetAnalyzerTests(unittest.TestCase):
    def test_classifies_fees_add_ons_and_credits(self) -> None:
        result = analyze_offer_sheet(
            advertised_price=25000,
            state="TX",
            line_items=[
                {"label": "Sales Tax", "amount": 1562.50},
                {"label": "Documentation Fee", "amount": 899},
                {"label": "VIN Etching", "amount": 499},
                {"label": "Dealer Discount", "amount": -1000},
                {"label": "Premium Handling", "amount": 250},
            ],
        )

        categories = {
            item["label"]: item["category"] for item in result["classified_items"]
        }
        self.assertEqual(categories["Sales Tax"], "government_charge")
        self.assertEqual(categories["Documentation Fee"], "dealer_fee")
        self.assertEqual(categories["VIN Etching"], "optional_product")
        self.assertEqual(categories["Dealer Discount"], "price_adjustment")
        self.assertEqual(categories["Premium Handling"], "unknown")
        self.assertEqual(result["totals"]["line_items_subtotal"], 2210.50)
        self.assertEqual(result["totals"]["out_the_door_total"], 27210.50)
        self.assertEqual(result["totals"]["potential_review_amount"], 1648)

    def test_positive_market_adjustment_is_flagged(self) -> None:
        result = analyze_offer_sheet(
            advertised_price=20000,
            line_items=[{"label": "Market Adjustment", "amount": 2500}],
        )
        item = result["classified_items"][0]
        self.assertEqual(item["category"], "price_adjustment")
        self.assertTrue(item["review_recommended"])
        self.assertEqual(result["review_level"], "high")

    def test_questions_use_neutral_language(self) -> None:
        result = analyze_offer_sheet(
            advertised_price=18000,
            line_items=[{"label": "Protection Package", "amount": 1200}],
        )
        combined = " ".join(
            f"{row['question']} {row['context']}" for row in result["questions"]
        ).lower()
        for accusatory_term in ("scam", "deceptive", "fraud", "useless"):
            self.assertNotIn(accusatory_term, combined)

    def test_rejects_missing_line_items(self) -> None:
        with self.assertRaises(OfferSheetError):
            analyze_offer_sheet(advertised_price=20000, line_items=[])


if __name__ == "__main__":
    unittest.main()
