import unittest
from unittest.mock import patch

from fetch_marketcheck import _closest_search_attempts, search_by_criteria


class ClosestListingsTests(unittest.TestCase):
    def test_closest_attempts_expand_year_first(self) -> None:
        attempts = _closest_search_attempts(
            {
                "make": "Subaru",
                "model": "Forester",
                "year": 2023,
                "max_price": 30000,
                "zip_code": "77002",
            },
            radius=100,
        )
        self.assertGreaterEqual(len(attempts), 2)
        first = attempts[0]["criteria"]
        self.assertNotIn("year", first)
        self.assertEqual(first["year_min"], 2022)
        self.assertEqual(first["year_max"], 2024)

    def test_search_returns_closest_notice_when_exact_empty(self) -> None:
        empty = {"num_found": 0, "listings": [], "stats": {}}
        filled = {
            "num_found": 2,
            "listings": [{"id": "1", "heading": "2022 Subaru Forester", "price": 28000}],
            "stats": {},
        }

        with patch("fetch_marketcheck._request", side_effect=[empty, filled]), patch(
            "fetch_marketcheck.normalize_listing",
            side_effect=lambda item: item,
        ):
            result = search_by_criteria(
                {
                    "make": "Subaru",
                    "model": "Forester",
                    "year": 2023,
                    "zip_code": "77002",
                    "max_price": 25000,
                },
                enrich_prices=False,
            )

        self.assertEqual(result["match_quality"], "closest")
        self.assertIn("closest to what you're looking for", result["match_notice"])
        self.assertEqual(len(result["listings"]), 1)


if __name__ == "__main__":
    unittest.main()
