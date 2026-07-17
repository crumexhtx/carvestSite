"""Soft-launch product feedback storage."""

import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import requests

from email_validation import EmailValidationError, normalize_email


ALLOWED_CATEGORIES = {"bug", "idea", "other"}


class FeedbackError(Exception):
    pass


def _backend() -> str:
    configured = os.environ.get("FEEDBACK_STORE_BACKEND", "auto").strip().lower()
    if configured != "auto":
        return configured
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        return "supabase"
    return "sqlite"


def _sqlite_path() -> Path:
    configured = os.environ.get("FEEDBACK_SQLITE_PATH", "").strip()
    return Path(configured) if configured else Path(__file__).parent / ".cache" / "feedback.sqlite3"


def _sqlite_connection() -> sqlite3.Connection:
    path = _sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS product_feedback (
            id TEXT PRIMARY KEY,
            email TEXT,
            category TEXT NOT NULL,
            message TEXT NOT NULL,
            page_path TEXT,
            created_at REAL NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def _normalize_email(email: Optional[str]) -> Optional[str]:
    try:
        return normalize_email(email or "", required=False)
    except EmailValidationError as exc:
        raise FeedbackError("Enter a valid email address, or leave it blank.") from exc


def submit_feedback(
    *,
    message: str,
    category: str = "other",
    email: Optional[str] = None,
    page_path: Optional[str] = None,
) -> dict[str, Any]:
    cleaned_message = " ".join(str(message or "").split()).strip()
    if len(cleaned_message) < 10:
        raise FeedbackError("Please share a bit more detail (at least 10 characters).")
    if len(cleaned_message) > 4000:
        raise FeedbackError("Feedback is limited to 4,000 characters.")

    cleaned_category = str(category or "other").strip().lower()
    if cleaned_category not in ALLOWED_CATEGORIES:
        raise FeedbackError("Choose a valid feedback category.")

    record = {
        "id": str(uuid.uuid4()),
        "email": _normalize_email(email),
        "category": cleaned_category,
        "message": cleaned_message,
        "page_path": (page_path or "").strip()[:200] or None,
        "created_at": time.time(),
    }

    if _backend() == "supabase":
        url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        table = os.environ.get("SUPABASE_FEEDBACK_TABLE", "product_feedback").strip()
        if not url or not key:
            raise FeedbackError("Feedback storage is not configured.")
        response = requests.post(
            f"{url}/rest/v1/{table}",
            json=record,
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            timeout=10,
        )
        if not response.ok:
            raise FeedbackError(f"Could not save feedback: {response.text}")
        rows = response.json() if response.content else [record]
        return rows[0] if rows else record

    connection = _sqlite_connection()
    try:
        connection.execute(
            """
            INSERT INTO product_feedback(id, email, category, message, page_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["email"],
                record["category"],
                record["message"],
                record["page_path"],
                record["created_at"],
            ),
        )
        connection.commit()
    finally:
        connection.close()
    return record
