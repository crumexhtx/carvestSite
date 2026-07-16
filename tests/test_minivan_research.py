import unittest
from unittest.mock import patch

from assistant_research import (
    _detect_use_cases,
    _pick_candidate_models,
    build_highlights,
    build_research_bundle,
)
from vehicle_assistant import _normalize_criteria


class MinivanResearchTests(unittest.TestCase):
    def test_detects_minivan_from_message(self) -> None:
        self.assertIn(
            "minivan",
            _detect_use_cases("Minivan with the best cargo space"),
        )

    def test_keeps_minivan_context_on_follow_up_message(self) -> None:
        criteria = {"use_case": "minivan", "body_type": "Minivan"}
        picks = _pick_candidate_models(criteria, "nothing appeared")
        models = {(item["make"], item["model"]) for item in picks}
        self.assertIn(("Toyota", "Sienna"), models)
        self.assertIn(("Honda", "Odyssey"), models)

    def test_normalize_promotes_use_case_to_body_type(self) -> None:
        normalized = _normalize_criteria({"use_case": "minivan"})
        self.assertEqual(normalized["body_type"], "Minivan")

    def test_research_bundle_builds_minivan_highlights(self) -> None:
        with (
            patch(
                "assistant_research.verify_vehicle_exists",
                side_effect=lambda make, year, model: (True, "ok", model),
            ),
            patch(
                "assistant_research.get_live_recalls",
                return_value={"total_recalls_count": 0, "recalls_list": []},
            ),
            patch("assistant_research._sample_listing", return_value={}),
            patch(
                "assistant_research.resolve_vehicle_photo",
                return_value={"photo": None, "photo_source": None},
            ),
        ):
            bundle = build_research_bundle(
                {"use_case": "minivan"},
                "nothing appeared",
            )
            highlights = build_highlights(bundle, {"use_case": "minivan"})

        self.assertGreaterEqual(len(bundle["candidate_models"]), 2)
        self.assertGreaterEqual(len(highlights), 2)


if __name__ == "__main__":
    unittest.main()
