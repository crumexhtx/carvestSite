import unittest

from email_validation import EmailValidationError, normalize_email
from home_insights import reliability_reference_year


class EmailValidationTests(unittest.TestCase):
    def test_accepts_normal_email(self) -> None:
        self.assertEqual(normalize_email("Buyer@Example.com"), "buyer@example.com")

    def test_rejects_incomplete_domain(self) -> None:
        with self.assertRaises(EmailValidationError):
            normalize_email("buyer@example")

    def test_optional_blank(self) -> None:
        self.assertIsNone(normalize_email("", required=False))


class ReliabilityYearTests(unittest.TestCase):
    def test_reference_year_is_recent(self) -> None:
        year = reliability_reference_year()
        self.assertGreaterEqual(year, 2020)
        self.assertLessEqual(year, 2100)


if __name__ == "__main__":
    unittest.main()
