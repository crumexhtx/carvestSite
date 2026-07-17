import os
import unittest
from unittest.mock import patch

from competitors import get_competitors
from fetch_marketcheck import enrich_listings_with_pricing
from openai_client import OpenAIConfigurationError, get_openai_client
from startup_checks import collect_production_config_errors


class OpenAILazyClientTests(unittest.TestCase):
    def test_missing_key_raises_configuration_error(self) -> None:
        import openai_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            with patch.object(openai_client, "_CLIENT", None):
                with self.assertRaises(OpenAIConfigurationError):
                    get_openai_client()


class StartupConfigTests(unittest.TestCase):
    def test_production_requires_origins_and_secrets(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
                "ALLOWED_ORIGINS": "",
                "CACHE_BACKEND": "upstash",
                "UPSTASH_REDIS_REST_URL": "",
                "UPSTASH_REDIS_REST_TOKEN": "",
                "REPORT_STORE_BACKEND": "supabase",
                "SUPABASE_URL": "",
                "SUPABASE_SERVICE_ROLE_KEY": "",
                "REPORT_ACCESS_SECRET": "",
            },
            clear=False,
        ):
            errors = collect_production_config_errors()
        self.assertTrue(any("ALLOWED_ORIGINS" in error for error in errors))
        self.assertTrue(any("UPSTASH" in error for error in errors))
        self.assertTrue(any("SUPABASE" in error for error in errors))
        self.assertTrue(any("REPORT_ACCESS_SECRET" in error for error in errors))

    def test_development_skips_production_guards(self) -> None:
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=False):
            self.assertEqual(collect_production_config_errors(), [])


class CompetitorSegmentFallbackTests(unittest.TestCase):
    def test_unmapped_segment_member_uses_segment_peers(self) -> None:
        # Mazda3 is listed under compact_sedan segment but may not have a model entry.
        result = get_competitors("Mazda", "Mazda3", limit=4)
        self.assertEqual(result["source"], "segment_fallback")
        self.assertEqual(result["segment"], "compact_sedan")
        self.assertGreaterEqual(len(result["competitors"]), 1)
        self.assertTrue(
            all(
                not (
                    item["make"].lower() == "mazda"
                    and item["model"].lower() == "mazda3"
                )
                for item in result["competitors"]
            )
        )


class MarketCheckEnrichmentTests(unittest.TestCase):
    def test_string_prices_and_failed_prediction_count_toward_budget(self) -> None:
        listings = [
            {"vin": "1", "miles": "10000", "price": "20000"},
            {"vin": "2", "miles": "20000", "price": "21000"},
            {"vin": "3", "miles": "30000", "price": "22000"},
        ]

        def fake_predict(*, vin, miles, zip_code):
            if vin == "1":
                raise __import__("fetch_marketcheck").MarketCheckError("down")
            return {"predicted_price": "19000"}

        with patch("fetch_marketcheck.predict_market_price", side_effect=fake_predict):
            enriched = enrich_listings_with_pricing(
                listings, zip_code="77087", max_predictions=2
            )

        self.assertIsNone(enriched[0].get("price_analysis"))
        self.assertTrue(enriched[0].get("price_analysis_error"))
        self.assertEqual(enriched[1]["price_analysis"]["predicted_fair_price"], 19000.0)
        self.assertEqual(enriched[1]["price"], 21000.0)
        # Third listing should not attempt prediction once budget is exhausted.
        self.assertIsNone(enriched[2].get("price_analysis"))
        self.assertIsNone(enriched[2].get("price_analysis_error"))


class ApiValidationTests(unittest.TestCase):
    def test_vehicle_query_rejects_non_numeric_year(self) -> None:
        from api_server import VehicleQuery
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            VehicleQuery(make="Honda", year="abc", model="Civic")

    def test_assistant_request_truncates_history(self) -> None:
        from api_server import AssistantChatRequest

        history = [
            {"role": "user", "content": f"message-{index}"} for index in range(30)
        ]
        payload = AssistantChatRequest(
            message="hello",
            criteria={"make": "Honda", "nested": {"ignored": True}},
            history=history,
        )
        self.assertEqual(len(payload.history or []), 20)
        self.assertEqual(payload.history[0]["content"], "message-10")
        self.assertIsInstance(payload.criteria.get("nested"), str)


if __name__ == "__main__":
    unittest.main()
