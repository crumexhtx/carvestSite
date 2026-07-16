import unittest
from unittest.mock import patch

from vehicle_reference_image import resolve_vehicle_photo


class ReferenceImageTests(unittest.TestCase):
    def test_prefers_listing_photo(self) -> None:
        result = resolve_vehicle_photo(
            "https://cdn.example.com/listing.jpg",
            "Toyota",
            "Highlander",
            2023,
        )
        self.assertEqual(result["photo"], "https://cdn.example.com/listing.jpg")
        self.assertEqual(result["photo_source"], "listing")

    def test_falls_back_to_reference_image(self) -> None:
        with patch(
            "vehicle_reference_image.get_reference_image",
            return_value={
                "photo": "https://upload.wikimedia.org/example.jpg",
                "photo_source": "reference",
                "provider": "wikipedia",
            },
        ):
            result = resolve_vehicle_photo(None, "Honda", "Pilot", 2022)
        self.assertEqual(result["photo_source"], "reference")
        self.assertIn("wikimedia", result["photo"])


if __name__ == "__main__":
    unittest.main()
