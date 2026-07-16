import unittest

from vehicle_assistant import (
    _extract_trim_from_message,
    _is_broad_vehicle_pivot,
    _looks_like_vehicle_name,
)
from vehicle_reference_image import get_reference_image


class TitleAndPivotTests(unittest.TestCase):
    def test_does_not_capture_full_vehicle_as_trim(self) -> None:
        criteria = {"make": "GMC", "model": "Hummer EV SUV", "year": 2021}
        trim = _extract_trim_from_message(
            "I'm interested in the 2021 GMC Hummer EV SUV",
            criteria,
        )
        self.assertIsNone(trim)

    def test_vehicle_shaped_trim_is_rejected(self) -> None:
        self.assertTrue(
            _looks_like_vehicle_name(
                "2021 Gmc Hummer Ev Suv",
                {"make": "GMC", "model": "Hummer EV SUV"},
            )
        )

    def test_broad_ev_suv_query_pivots_off_hummer(self) -> None:
        criteria = {"make": "GMC", "model": "Hummer EV SUV", "year": 2021}
        self.assertTrue(
            _is_broad_vehicle_pivot("I am looking for SUVs that are EVs", criteria)
        )

    def test_mileage_follow_up_does_not_pivot(self) -> None:
        criteria = {"make": "GMC", "model": "Hummer EV SUV", "year": 2021}
        self.assertFalse(
            _is_broad_vehicle_pivot("I want listings under 50,000 miles", criteria)
        )

    def test_hummer_ev_suv_resolves_reference_image(self) -> None:
        resolved = get_reference_image("GMC", "Hummer EV SUV")
        self.assertIsNotNone(resolved)
        self.assertTrue(str(resolved.get("photo", "")).startswith("http"))


if __name__ == "__main__":
    unittest.main()
