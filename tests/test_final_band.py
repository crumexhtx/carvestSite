import os
import unittest
from unittest.mock import patch

from listing_trust import attach_listing_trust, sign_listing, verify_listing_trust
from rate_limit import ApiRateLimitMiddleware


class ListingTrustTests(unittest.TestCase):
    def test_round_trip_signature(self) -> None:
        with patch.dict(os.environ, {"LISTING_TRUST_SECRET": "unit-test-secret"}):
            listing = {
                "listing_id": "abc123",
                "vin": "1HGCM82633A004352",
                "price": 20000,
                "miles": 45000,
                "vdp_url": "https://dealer.example/car",
                "dealer_name": "Example Motors",
                "price_analysis": {
                    "predicted_fair_price": 19000.0,
                    "deal_signal": "NEAR_MARKET",
                },
            }
            signed = attach_listing_trust(listing)
            self.assertTrue(
                verify_listing_trust(
                    listing_id="abc123",
                    vin="1HGCM82633A004352",
                    price=20000,
                    miles=45000,
                    vdp_url="https://dealer.example/car",
                    predicted_fair_price=19000,
                    deal_signal="NEAR_MARKET",
                    dealer_name="Example Motors",
                    trust_sig=signed["trust_sig"],
                )
            )

    def test_tampered_price_fails(self) -> None:
        with patch.dict(os.environ, {"LISTING_TRUST_SECRET": "unit-test-secret"}):
            listing = {
                "listing_id": "abc123",
                "price": 20000,
                "miles": 1000,
                "vdp_url": "https://dealer.example/car",
            }
            sig = sign_listing(listing)
            self.assertFalse(
                verify_listing_trust(
                    listing_id="abc123",
                    price=1000,
                    miles=1000,
                    vdp_url="https://dealer.example/car",
                    trust_sig=sig,
                )
            )


class RateLimitBackendTests(unittest.TestCase):
    def test_memory_limiter_blocks_after_budget(self) -> None:
        with patch.dict(
            os.environ,
            {
                "API_RATE_LIMIT_ENABLED": "true",
                "API_RATE_LIMIT_REQUESTS": "2",
                "API_RATE_LIMIT_WINDOW_SECONDS": "60",
                "API_RATE_LIMIT_BACKEND": "memory",
            },
        ):
            middleware = ApiRateLimitMiddleware(app=lambda: None)
            key = "1.2.3.4:/api/negotiation"
            self.assertTrue(middleware._allow(key)[0])
            self.assertTrue(middleware._allow(key)[0])
            allowed, retry_after = middleware._allow(key)
            self.assertFalse(allowed)
            self.assertGreaterEqual(retry_after, 1)


if __name__ == "__main__":
    unittest.main()
