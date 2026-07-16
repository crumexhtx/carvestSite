import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import cache_backend
import fetch_marketcheck


class CacheBackendTests(unittest.TestCase):
    def test_cache_keys_are_stable_for_reordered_payloads(self) -> None:
        first = cache_backend.build_cache_key("test", {"b": 2, "a": 1})
        second = cache_backend.build_cache_key("test", {"a": 1, "b": 2})
        self.assertEqual(first, second)

    def test_sqlite_cache_round_trip_and_expiration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "cache.sqlite3"
            with patch.dict(
                os.environ,
                {
                    "CACHE_BACKEND": "sqlite",
                    "CACHE_SQLITE_PATH": str(cache_path),
                },
            ):
                cache_backend.set_json("round-trip", {"ok": True}, 1)
                self.assertEqual(cache_backend.get_json("round-trip"), {"ok": True})
                time.sleep(1.05)
                self.assertIsNone(cache_backend.get_json("round-trip"))

    def test_marketcheck_request_returns_cached_response_without_http(self) -> None:
        cached = {"num_found": 42, "listings": []}
        with (
            patch.object(fetch_marketcheck, "get_json", return_value=cached),
            patch.object(fetch_marketcheck.requests, "get") as http_get,
        ):
            result = fetch_marketcheck._request(
                "/search/car/active",
                {"make": "Toyota", "rows": 1},
            )
        self.assertEqual(result, cached)
        http_get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
