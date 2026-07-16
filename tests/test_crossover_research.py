import unittest
from unittest.mock import patch

from assistant_research import (
    _detect_use_cases,
    _pick_candidate_models,
    build_highlights,
    build_research_bundle,
)
from vehicle_assistant import _highlights_from_summaries, _normalize_criteria


class CrossoverResearchTests(unittest.TestCase):
    def test_detects_crossover_from_message(self) -> None:
        self.assertIn(
            "crossover",
            _detect_use_cases("AWD crossover with strong resale"),
        )

    def test_normalize_maps_crossover_to_suv(self) -> None:
        normalized = _normalize_criteria({"body_type": "crossover"})
        self.assertEqual(normalized["body_type"], "SUV")

    def test_normalize_promotes_crossover_use_case(self) -> None:
        normalized = _normalize_criteria({"use_case": "crossover"})
        self.assertEqual(normalized["body_type"], "SUV")

    def test_picks_crv_forester_rav4(self) -> None:
        picks = _pick_candidate_models({}, "AWD crossover with strong resale")
        models = {(item["make"], item["model"]) for item in picks}
        self.assertIn(("Honda", "CR-V"), models)
        self.assertIn(("Subaru", "Forester"), models)
        self.assertIn(("Toyota", "RAV4"), models)

    def test_research_bundle_builds_crossover_highlights(self) -> None:
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
                return_value={"photo": "proxy.jpg", "photo_source": "reference"},
            ),
        ):
            bundle = build_research_bundle(
                {"body_type": "SUV", "drivetrain": "4WD"},
                "I'm interested in crossovers with under 50k miles.",
            )
            highlights = build_highlights(bundle, {"body_type": "SUV"})

        self.assertGreaterEqual(len(bundle["candidate_models"]), 2)
        self.assertGreaterEqual(len(highlights), 2)

    def test_summaries_backfill_highlights(self) -> None:
        with patch(
            "vehicle_reference_image.resolve_vehicle_photo",
            return_value={"photo": "proxy.jpg", "photo_source": "reference"},
        ):
            highlights = _highlights_from_summaries(
                [
                    {
                        "make": "Honda",
                        "model": "CR-V",
                        "sentence": "Strong resale compact crossover.",
                    },
                    {
                        "make": "Subaru",
                        "model": "Forester",
                        "sentence": "Standard AWD utility.",
                    },
                ],
                {"year_max": 2021},
            )
        self.assertEqual(len(highlights), 2)
        self.assertEqual(highlights[0]["year"], 2021)
        self.assertEqual(highlights[0]["photo"], "proxy.jpg")


if __name__ == "__main__":
    unittest.main()
