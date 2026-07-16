import hashlib
import hmac
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import requests


JSON_FIELDS = {"request_json", "preview_json", "full_json"}
UPDATABLE_FIELDS = {
    "status",
    "preview_json",
    "full_json",
    "stripe_session_id",
    "stripe_payment_intent_id",
    "paid_at",
    "updated_at",
}


class ReportStoreError(Exception):
    pass


def _access_secret() -> bytes:
    secret = os.environ.get("REPORT_ACCESS_SECRET", "").strip()
    if not secret:
        if os.environ.get("ENVIRONMENT", "development").lower() == "production":
            raise ReportStoreError("REPORT_ACCESS_SECRET is required in production.")
        secret = "carvest-local-development-only"
    return secret.encode("utf-8")


def access_token_for(report_id: str) -> str:
    return hmac.new(_access_secret(), report_id.encode("utf-8"), hashlib.sha256).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _backend() -> str:
    configured = os.environ.get("REPORT_STORE_BACKEND", "auto").strip().lower()
    if configured != "auto":
        return configured
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        return "supabase"
    return "sqlite"


def _sqlite_path() -> Path:
    configured = os.environ.get("REPORT_SQLITE_PATH", "").strip()
    return Path(configured) if configured else Path(__file__).parent / ".cache" / "reports.sqlite3"


def _sqlite_connection() -> sqlite3.Connection:
    path = _sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS buyer_reports (
            id TEXT PRIMARY KEY,
            access_token_hash TEXT NOT NULL,
            vin TEXT NOT NULL,
            email TEXT,
            request_json TEXT NOT NULL,
            preview_json TEXT NOT NULL,
            full_json TEXT,
            status TEXT NOT NULL,
            stripe_session_id TEXT,
            stripe_payment_intent_id TEXT,
            created_at REAL NOT NULL,
            paid_at REAL,
            updated_at REAL NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_buyer_reports_stripe_session "
        "ON buyer_reports(stripe_session_id)"
    )
    connection.commit()
    return connection


def _decode_sqlite_row(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    for field in JSON_FIELDS:
        if result.get(field):
            result[field] = json.loads(result[field])
    return result


def _supabase_config() -> tuple[str, str, str]:
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    table = os.environ.get("SUPABASE_REPORTS_TABLE", "buyer_reports").strip()
    if not url or not key:
        raise ReportStoreError("Supabase report storage is missing credentials.")
    return url, key, table


def _supabase_request(
    method: str,
    *,
    params: Optional[dict[str, str]] = None,
    payload: Optional[dict[str, Any]] = None,
) -> Any:
    url, key, table = _supabase_config()
    response = requests.request(
        method,
        f"{url}/rest/v1/{table}",
        params=params,
        json=payload,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        timeout=10,
    )
    if not response.ok:
        raise ReportStoreError(f"Supabase report storage error: {response.text}")
    return response.json() if response.content else None


def create_report(
    *,
    vin: str,
    email: Optional[str],
    request_data: dict[str, Any],
    preview: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    report_id = str(uuid.uuid4())
    access_token = access_token_for(report_id)
    now = time.time()
    record = {
        "id": report_id,
        "access_token_hash": _token_hash(access_token),
        "vin": vin,
        "email": email,
        "request_json": request_data,
        "preview_json": preview,
        "full_json": None,
        "status": "pending_payment",
        "stripe_session_id": None,
        "stripe_payment_intent_id": None,
        "created_at": now,
        "paid_at": None,
        "updated_at": now,
    }

    if _backend() == "supabase":
        rows = _supabase_request("POST", payload=record)
        return rows[0], access_token

    connection = _sqlite_connection()
    try:
        encoded = dict(record)
        for field in JSON_FIELDS:
            if encoded.get(field) is not None:
                encoded[field] = json.dumps(encoded[field], separators=(",", ":"), default=str)
        columns = ", ".join(encoded.keys())
        placeholders = ", ".join("?" for _ in encoded)
        connection.execute(
            f"INSERT INTO buyer_reports ({columns}) VALUES ({placeholders})",
            tuple(encoded.values()),
        )
        connection.commit()
    finally:
        connection.close()
    return record, access_token


def get_report(report_id: str) -> Optional[dict[str, Any]]:
    if _backend() == "supabase":
        rows = _supabase_request(
            "GET",
            params={"id": f"eq.{report_id}", "select": "*", "limit": "1"},
        )
        return rows[0] if rows else None

    connection = _sqlite_connection()
    try:
        row = connection.execute(
            "SELECT * FROM buyer_reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        return _decode_sqlite_row(row) if row else None
    finally:
        connection.close()


def get_authorized_report(report_id: str, token: str) -> Optional[dict[str, Any]]:
    record = get_report(report_id)
    if not record or not token:
        return None
    if not hmac.compare_digest(str(record["access_token_hash"]), _token_hash(token)):
        return None
    return record


def update_report(report_id: str, **updates: Any) -> dict[str, Any]:
    clean = {key: value for key, value in updates.items() if key in UPDATABLE_FIELDS}
    clean["updated_at"] = time.time()

    if _backend() == "supabase":
        rows = _supabase_request(
            "PATCH",
            params={"id": f"eq.{report_id}"},
            payload=clean,
        )
        if not rows:
            raise ReportStoreError("Report not found.")
        return rows[0]

    encoded = dict(clean)
    for field in JSON_FIELDS:
        if field in encoded and encoded[field] is not None:
            encoded[field] = json.dumps(encoded[field], separators=(",", ":"), default=str)
    assignments = ", ".join(f"{field} = ?" for field in encoded)
    connection = _sqlite_connection()
    try:
        cursor = connection.execute(
            f"UPDATE buyer_reports SET {assignments} WHERE id = ?",
            (*encoded.values(), report_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            raise ReportStoreError("Report not found.")
    finally:
        connection.close()
    record = get_report(report_id)
    if not record:
        raise ReportStoreError("Report not found.")
    return record
