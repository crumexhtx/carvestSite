import sys
import time
from typing import Any
from urllib.parse import quote

import requests

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

RECALLS_REQUEST_TIMEOUT = 6
RECALLS_SUCCESS_TTL_SECONDS = 3600
RECALLS_ERROR_TTL_SECONDS = 300

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _cache_key(make: str, year: str | int, model: str) -> str:
    return f"{str(make).strip().lower()}|{str(year).strip()}|{str(model).strip().lower()}"


def clear_recalls_cache() -> None:
    _CACHE.clear()


def get_live_recalls(
    make,
    year,
    model,
    *,
    verbose: bool = True,
    timeout: float = RECALLS_REQUEST_TIMEOUT,
    use_cache: bool = True,
):
    """
    Queries the official NHTSA database for active safety recalls
    on a specific vehicle model. Results are cached in memory.
    """
    clean_make = str(make).strip()
    clean_model = str(model).strip()
    clean_year = str(year).strip()
    key = _cache_key(clean_make, clean_year, clean_model)

    if use_cache:
        cached = _CACHE.get(key)
        if cached:
            expires_at, payload = cached
            if time.time() < expires_at:
                if verbose:
                    print(
                        f"📦 Using cached recalls for {clean_year} {clean_make} {clean_model}"
                    )
                return dict(payload)

    if verbose:
        print(
            f"📡 Fetching live government recalls for {clean_year} {clean_make} {clean_model}..."
        )

    url = (
        "https://api.nhtsa.gov/recalls/recallsByVehicle"
        f"?make={quote(clean_make)}&model={quote(clean_model)}&modelYear={quote(clean_year)}"
    )

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        clean_recalls = []

        for item in results:
            clean_recalls.append(
                {
                    "Component": item.get("Component", "Unknown Component"),
                    "Summary": item.get("Summary", "No summary provided by manufacturer."),
                    "Consequence": item.get(
                        "Consequence", "No immediate consequence listed."
                    ),
                    "Remedy": item.get("Remedy", "No official remedy detailed yet."),
                }
            )

        payload = {
            "total_recalls_count": data.get("Count", 0),
            "recalls_list": clean_recalls,
        }
        if use_cache:
            _CACHE[key] = (time.time() + RECALLS_SUCCESS_TTL_SECONDS, payload)
        return payload

    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"❌ Error talking to NHTSA Recalls API: {e}")
        payload = {
            "total_recalls_count": 0,
            "recalls_list": [],
            "error": str(e),
        }
        if use_cache:
            _CACHE[key] = (time.time() + RECALLS_ERROR_TTL_SECONDS, payload)
        return payload


def get_live_recalls_many(
    requests_list: list[tuple[str, int | str, str]],
    *,
    max_workers: int = 3,
    overall_timeout: float = 12,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """Fetch multiple recall lookups with bounded parallelism."""
    if not requests_list:
        return []

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch(item: tuple[str, int | str, str]) -> dict[str, Any]:
        make, year, model = item
        recalls = get_live_recalls(make, year, model, verbose=verbose)
        return {
            "make": make,
            "year": int(year),
            "model": model,
            **recalls,
        }

    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_fetch, item) for item in requests_list]
        try:
            for future in as_completed(futures, timeout=overall_timeout):
                try:
                    rows.append(future.result())
                except Exception:
                    continue
        except TimeoutError:
            for future in futures:
                future.cancel()

    return rows


if __name__ == "__main__":
    test_data = get_live_recalls(make="Ford", year=2015, model="Explorer")

    print("\n--- TEST SCRIPT RESULTS ---")
    print(f"Total Recalls Found: {test_data['total_recalls_count']}")
    if test_data["recalls_list"]:
        print("Sample of First Recall Component:", test_data["recalls_list"][0]["Component"])
