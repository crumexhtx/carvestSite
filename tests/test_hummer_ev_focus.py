import unittest

from vehicle_assistant import (
    _extract_make_model_from_message,
    _infer_phase,
    _normalize_criteria,
)


class HummerEvFocusTests(unittest.TestCase):
    def test_extracts_hummer_ev_as_gmc_suv(self) -> None:
        updates = _extract_make_model_from_message(
            "i want to know about the Hummer EV",
            {},
        )
        self.assertEqual(updates.get("make"), "GMC")
        self.assertEqual(updates.get("model"), "Hummer EV SUV")

    def test_extracts_hummer_ev_pickup(self) -> None:
        updates = _extract_make_model_from_message(
            "Tell me about the Hummer EV pickup",
            {},
        )
        self.assertEqual(updates.get("make"), "GMC")
        self.assertEqual(updates.get("model"), "Hummer EV Pickup")

    def test_named_hummer_enters_model_focus(self) -> None:
        criteria = _normalize_criteria(
            _extract_make_model_from_message("i want to know about the Hummer EV", {})
        )
        phase = _infer_phase(criteria, "i want to know about the Hummer EV", {})
        self.assertEqual(phase, "model_focus")
        self.assertEqual(criteria["make"], "GMC")
        self.assertEqual(criteria["model"], "Hummer EV SUV")


if __name__ == "__main__":
    unittest.main()
