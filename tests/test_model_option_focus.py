import unittest

from vehicle_assistant import (
    _has_model_option_focus,
    _infer_phase,
    _response_mode,
)


class ModelOptionFocusTests(unittest.TestCase):
    def test_broad_model_pick_is_model_focus(self) -> None:
        criteria = {"make": "Toyota", "model": "Tundra"}
        self.assertFalse(_has_model_option_focus(criteria))
        phase = _infer_phase(
            criteria,
            "I'm interested in the Toyota Tundra. Tell me which years are best and what to avoid.",
            {},
        )
        self.assertEqual(phase, "model_focus")
        self.assertEqual(_response_mode(phase), "model_focus")

    def test_year_pick_switches_to_option_focus(self) -> None:
        criteria = {"make": "Toyota", "model": "Tundra", "year": 2021}
        self.assertTrue(_has_model_option_focus(criteria))
        phase = _infer_phase(criteria, "I'm interested in the 2021 Toyota Tundra", {})
        self.assertEqual(phase, "option_focus")
        self.assertEqual(_response_mode(phase), "option_focus")

    def test_trim_or_mileage_is_option_focus(self) -> None:
        self.assertTrue(
            _has_model_option_focus(
                {"make": "Toyota", "model": "Tundra", "trim": "TRD Pro"}
            )
        )
        self.assertTrue(
            _has_model_option_focus(
                {"make": "Toyota", "model": "Tundra", "max_miles": 50000}
            )
        )

    def test_search_ready_still_wins(self) -> None:
        criteria = {
            "make": "Toyota",
            "model": "Tundra",
            "year": 2021,
            "zip_code": "77002",
            "max_price": 35000,
        }
        phase = _infer_phase(criteria, "ready", {})
        self.assertEqual(phase, "search_ready")


if __name__ == "__main__":
    unittest.main()
