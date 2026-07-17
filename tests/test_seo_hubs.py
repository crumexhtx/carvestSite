import unittest
from unittest.mock import patch

from seo_hubs import curated_hubs, get_model_brief, resolve_vehicle, slugify


class SeoHubTests(unittest.TestCase):
    def test_slugify(self) -> None:
        self.assertEqual(slugify("Silverado 1500"), "silverado-1500")
        self.assertEqual(slugify("CR-V"), "cr-v")

    def test_resolve_catalog_vehicle(self) -> None:
        resolved = resolve_vehicle("honda", "civic", 2023)
        self.assertIsNotNone(resolved)
        assert resolved is not None
        make, model, year = resolved
        self.assertEqual(make, "Honda")
        self.assertEqual(model, "Civic")
        self.assertEqual(year, 2023)

    def test_resolve_model_alias(self) -> None:
        resolved = resolve_vehicle("toyota", "corolla-hybrid", 2023)
        self.assertIsNotNone(resolved)
        assert resolved is not None
        self.assertEqual(resolved[0], "Toyota")
        self.assertEqual(resolved[1], "Corolla")

    def test_curated_hubs_non_empty(self) -> None:
        hubs = curated_hubs()
        self.assertGreaterEqual(len(hubs), 5)
        paths = {hub["path"] for hub in hubs}
        self.assertTrue(any(path.startswith("/cars/") for path in paths))
        for hub in hubs:
            self.assertIn("make_slug", hub)
            self.assertIn("model_slug", hub)
            self.assertTrue(hub["path"].startswith("/cars/"))

    def test_model_brief_includes_recalls_shape(self) -> None:
        fake_recalls = {
            "available": True,
            "total_recalls_count": 1,
            "recalls_list": [
                {
                    "Component": "AIR BAGS",
                    "Summary": "Inflator may rupture.",
                    "Consequence": "Injury risk.",
                    "Remedy": "Replace inflator.",
                }
            ],
        }
        with patch("seo_hubs.get_live_recalls", return_value=fake_recalls):
            brief = get_model_brief("honda", "civic", 2023)
        self.assertIsNotNone(brief)
        assert brief is not None
        self.assertEqual(brief["make"], "Honda")
        self.assertEqual(brief["model"], "Civic")
        self.assertTrue(brief["recalls"]["available"])
        self.assertEqual(brief["recalls"]["total_recalls_count"], 1)
        self.assertEqual(brief["recalls"]["items"][0]["component"], "AIR BAGS")
        self.assertIn("/cars/honda/civic/2023", brief["path"])

    def test_unknown_vehicle_returns_none(self) -> None:
        self.assertIsNone(resolve_vehicle("not-a-make", "nope", 2023))
        self.assertIsNone(get_model_brief("not-a-make", "nope", 2023))


if __name__ == "__main__":
    unittest.main()
