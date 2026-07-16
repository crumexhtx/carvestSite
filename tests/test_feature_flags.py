import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import feature_flags
from waitlist_store import WaitlistError, add_waitlist_email


class FeatureFlagTests(unittest.TestCase):
    def test_monetization_defaults_to_off(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MONETIZATION_ENABLED", None)
            self.assertFalse(feature_flags.monetization_enabled())

    def test_monetization_can_be_enabled(self) -> None:
        with patch.dict(os.environ, {"MONETIZATION_ENABLED": "true"}):
            self.assertTrue(feature_flags.monetization_enabled())

    def test_waitlist_stores_normalized_email(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(
                os.environ,
                {
                    "WAITLIST_STORE_BACKEND": "sqlite",
                    "WAITLIST_SQLITE_PATH": str(Path(directory) / "waitlist.sqlite3"),
                },
            ):
                result = add_waitlist_email("Buyer@Example.COM", "unit_test")
                self.assertEqual(result["email"], "buyer@example.com")
                again = add_waitlist_email("buyer@example.com", "unit_test")
                self.assertEqual(again["email"], "buyer@example.com")

    def test_waitlist_rejects_invalid_email(self) -> None:
        with self.assertRaises(WaitlistError):
            add_waitlist_email("not-an-email")


if __name__ == "__main__":
    unittest.main()
