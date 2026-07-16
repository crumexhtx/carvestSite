import unittest

from assistant_research import (
    _build_narrowing_options,
    model_drivetrain_options,
    model_trim_options,
)
from vehicle_assistant import (
    _extract_criteria_from_message,
    _narrowing_guidance,
    _normalize_criteria,
)


class PriusTrimFlowTests(unittest.TestCase):
    def test_prius_trims_are_le_xle_limited(self) -> None:
        self.assertEqual(model_trim_options("Toyota", "Prius"), ["LE", "XLE", "Limited"])

    def test_prius_is_fwd_only(self) -> None:
        self.assertEqual(model_drivetrain_options("Toyota", "Prius"), ["FWD"])

    def test_normalize_autosets_prius_fwd(self) -> None:
        normalized = _normalize_criteria({"make": "Toyota", "model": "Prius", "year": 2023})
        self.assertEqual(normalized["drivetrain"], "FWD")

    def test_narrowing_asks_trim_not_4wd_for_prius(self) -> None:
        criteria = _normalize_criteria({"make": "Toyota", "model": "Prius", "year": 2023})
        guidance = _narrowing_guidance(criteria, [{"role": "user", "content": "hi"}] * 2)
        self.assertEqual(guidance["suggested_next_question"], "ask_trim")

        options = _build_narrowing_options(
            "ask_trim",
            criteria,
            {},
            None,
            "option_focus",
        )
        labels = [item["label"] for item in options]
        self.assertEqual(labels[:3], ["LE", "XLE", "Limited"])
        self.assertNotIn("4WD", labels)
        self.assertNotIn("Base trim", labels)

    def test_base_trim_message_maps_to_le_and_advances(self) -> None:
        criteria = _normalize_criteria({"make": "Toyota", "model": "Prius", "year": 2023})
        updates = _extract_criteria_from_message(
            "Tell me about base trim options for the Toyota Prius",
            criteria,
        )
        self.assertEqual(updates.get("trim"), "LE")
        merged = _normalize_criteria({**criteria, **updates})
        guidance = _narrowing_guidance(merged, [{"role": "user", "content": "x"}] * 3)
        self.assertEqual(guidance["suggested_next_question"], "ask_max_mileage")


if __name__ == "__main__":
    unittest.main()
