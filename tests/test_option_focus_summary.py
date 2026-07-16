import unittest

from vehicle_assistant import _enrich_option_focus_summary


class OptionFocusSummaryTests(unittest.TestCase):
    def test_pads_to_three_sentences_with_owner_and_expert_views(self) -> None:
        summary = _enrich_option_focus_summary(
            "The 2021 Toyota Tundra is a solid full-size truck choice.",
            {"make": "Toyota", "model": "Tundra", "year": 2021},
        )
        sentences = [part for part in summary.replace("!", ".").split(".") if part.strip()]
        self.assertGreaterEqual(len(sentences), 3)
        lowered = summary.lower()
        self.assertTrue("owner" in lowered or "owners" in lowered)
        self.assertTrue(
            "expert" in lowered or "analyst" in lowered or "reviewer" in lowered
        )


if __name__ == "__main__":
    unittest.main()
