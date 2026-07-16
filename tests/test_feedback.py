import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from feedback_store import FeedbackError, submit_feedback


class FeedbackStoreTests(unittest.TestCase):
    def test_stores_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(
                os.environ,
                {
                    "FEEDBACK_STORE_BACKEND": "sqlite",
                    "FEEDBACK_SQLITE_PATH": str(Path(directory) / "feedback.sqlite3"),
                },
            ):
                result = submit_feedback(
                    message="The listing deal check was really helpful.",
                    category="idea",
                    email="tester@example.com",
                    page_path="/feedback",
                )
                self.assertEqual(result["category"], "idea")
                self.assertEqual(result["email"], "tester@example.com")

    def test_rejects_short_message(self) -> None:
        with self.assertRaises(FeedbackError):
            submit_feedback(message="Too short", category="other")


if __name__ == "__main__":
    unittest.main()
