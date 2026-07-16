"""Simple waitlist storage for soft-launch email capture."""

import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

import requests


class WaitlistError(Exception):
    pass


def _backend() -> str:
    configured = os.environ.get("WAITLIST_STORE_BACKEND", "auto").strip().lower()
    if configured != "auto":
        return configured
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        return "supabase"
    return "sqlite"


def _sqlite_path() -> Path:
    configured = os.environ.get("WAITLIST_SQLITE_PATH", "").strip()
    return Path(configured) if configured else Path(__file__).parent / ".cache" / "waitlist.sqlite3"


def _sqlite_connection() -> sqlite3.Connection:
    path = _sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS waitlist_emails (
            email TEXT PRIMARY KEY,
            source TEXT,
            created_at REAL NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def _normalize_email(email: str) -> str:
    cleaned = email.strip().lower()
    if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
        raise WaitlistError("Enter a valid email address.")
    if len(cleaned) > 254:
        raise WaitlistError("Email address is too long.")
    return cleaned


def _supabase_upsert(email: str, source: Optional[str]) -> dict[str, Any]:
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    table = os.environ.get("SUPABASE_WAITLIST_TABLE", "waitlist_emails").strip()
    if not url or not key:
        raise WaitlistError("Waitlist storage is not configured.")
    payload = {
        "email": email,
        "source": source or "soft_launch",
        "created_at": time.time(),
    }
    response = requests.post(
        f"{url}/rest/v1/{table}",
        params={"on_conflict": "email"},
        json=payload,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=representation",
        },
        timeout=10,
    )
    if not response.ok:
        raise WaitlistError(f"Could not save waitlist email: {response.text}")
    rows = response.json() if response.content else [payload]
    return rows[0] if rows else payload


def add_waitlist_email(email: str, source: Optional[str] = None) -> dict[str, Any]:
    normalized = _normalize_email(email)
    source_value = (source or "soft_launch").strip()[:80] or "soft_launch"

    if _backend() == "supabase":
        return _supabase_upsert(normalized, source_value)

    connection = _sqlite_connection()
    try:
        connection.execute(
            """
            INSERT INTO waitlist_emails(email, source, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                source = excluded.source
            """,
            (normalized, source_value, time.time()),
        )
        connection.commit()
    finally:
        connection.close()
    return {"email": normalized, "source": source_value, "status": "subscribed"}
