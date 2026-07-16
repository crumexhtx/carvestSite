import unittest

from assistant_research import (
    _detect_use_cases,
    _follow_up_prompt,
    _sanitize_ai_follow_up_options,
    build_follow_up_options,
)


class FollowUpChipTests(unittest.TestCase):
    def test_year_prompt_requires_all_year_chips(self) -> None:
        mixed = [
            {"label": "Sedan", "message": "Sedan"},
            {"label": "2022", "message": "2022"},
            {"label": "2021", "message": "2021"},
        ]
        prompt = _follow_up_prompt({}, {"suggested_next_question": ""}, mixed, "discover")
        self.assertNotIn("years", prompt.lower())

    def test_sanitize_drops_body_types_on_year_question(self) -> None:
        cleaned = _sanitize_ai_follow_up_options(
            "ask_year_range",
            [
                {"label": "Sedan", "message": "Sedan"},
                {"label": "SUV", "message": "SUV"},
                {"label": "2022", "message": "Tell me about 2022"},
                {"label": "Tesla Model 3", "message": "Tesla Model 3"},
            ],
        )
        self.assertEqual([item["label"] for item in cleaned], ["2022"])

    def test_detects_electric_suv_query(self) -> None:
        self.assertIn(
            "electric",
            _detect_use_cases("electric SUVs with impressive range under $45,000"),
        )

    def test_discover_chips_come_from_highlights_only(self) -> None:
        result = build_follow_up_options(
            {},
            {},
            {"suggested_next_question": "ask_model_preference"},
            ai_options=[
                {"label": "Sedan", "message": "Sedan"},
                {"label": "2022", "message": "2022"},
            ],
            highlights=[
                {"make": "Ford", "model": "Mustang Mach-E"},
                {"make": "Hyundai", "model": "Ioniq 5"},
            ],
            response_mode="discover",
        )
        labels = [item["label"] for item in result["options"]]
        self.assertEqual(labels, ["Ford Mustang Mach-E", "Hyundai Ioniq 5"])
        self.assertEqual(result["prompt"], "Which model interests you most?")


if __name__ == "__main__":
    unittest.main()
