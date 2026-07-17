"""Production configuration guards for the Carvest API."""

from __future__ import annotations

import os
from typing import Optional


def _is_production() -> bool:
    return os.environ.get("ENVIRONMENT", "development").strip().lower() == "production"


def collect_production_config_errors() -> list[str]:
    if not _is_production():
        return []

    errors: list[str] = []

    if not os.environ.get("ALLOWED_ORIGINS", "").strip():
        errors.append("ALLOWED_ORIGINS must be set in production.")

    cache_backend = os.environ.get("CACHE_BACKEND", "auto").strip().lower()
    upstash_url = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip()
    upstash_token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "").strip()
    if cache_backend == "upstash" and not (upstash_url and upstash_token):
        errors.append(
            "CACHE_BACKEND=upstash requires UPSTASH_REDIS_REST_URL and "
            "UPSTASH_REDIS_REST_TOKEN."
        )

    report_backend = os.environ.get("REPORT_STORE_BACKEND", "auto").strip().lower()
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if report_backend == "supabase" and not (supabase_url and supabase_key):
        errors.append(
            "REPORT_STORE_BACKEND=supabase requires SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY."
        )

    if not os.environ.get("REPORT_ACCESS_SECRET", "").strip():
        errors.append("REPORT_ACCESS_SECRET must be set in production.")

    return errors


def validate_production_config() -> None:
    errors = collect_production_config_errors()
    if errors:
        raise RuntimeError("Invalid production configuration: " + " ".join(errors))


def production_allowed_origins_or_none() -> Optional[list[str]]:
    """Return configured origins, or None when unset (caller decides fallback)."""
    configured = os.environ.get("ALLOWED_ORIGINS", "")
    origins = [
        origin.strip().rstrip("/")
        for origin in configured.split(",")
        if origin.strip()
    ]
    return origins or None
