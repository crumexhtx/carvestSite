import hashlib
import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Optional

import requests


_LOCK = threading.Lock()
_MEMORY_CACHE: dict[str, tuple[float, Any]] = {}
_SQLITE_READY_PATH: Optional[Path] = None


def build_cache_key(namespace: str, payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"carvest:{namespace}:{digest}"


def _backend_name() -> str:
    configured = os.environ.get("CACHE_BACKEND", "auto").strip().lower()
    if configured != "auto":
        return configured
    if _upstash_config():
        return "upstash"
    return "sqlite"


def _upstash_config() -> Optional[tuple[str, str]]:
    url = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip().rstrip("/")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "").strip()
    if url and token:
        return url, token
    return None


def _sqlite_path() -> Path:
    configured = os.environ.get("CACHE_SQLITE_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).parent / ".cache" / "carvest.sqlite3"


def _ensure_sqlite() -> Path:
    global _SQLITE_READY_PATH
    path = _sqlite_path()
    with _LOCK:
        if _SQLITE_READY_PATH == path:
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=5)
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS api_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_api_cache_expires_at ON api_cache(expires_at)"
            )
            connection.commit()
        finally:
            connection.close()
        _SQLITE_READY_PATH = path
    return path


def _memory_get(key: str) -> Any:
    item = _MEMORY_CACHE.get(key)
    if not item:
        return None
    expires_at, payload = item
    if expires_at <= time.time():
        _MEMORY_CACHE.pop(key, None)
        return None
    return payload


def _memory_set(key: str, payload: Any, ttl_seconds: int) -> None:
    _MEMORY_CACHE[key] = (time.time() + ttl_seconds, payload)


def _sqlite_get(key: str) -> Any:
    path = _ensure_sqlite()
    now = time.time()
    connection = sqlite3.connect(path, timeout=5)
    try:
        cursor = connection.execute(
            "SELECT payload, expires_at FROM api_cache WHERE cache_key = ?",
            (key,),
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return None
        if float(row[1]) <= now:
            connection.execute("DELETE FROM api_cache WHERE cache_key = ?", (key,))
            connection.commit()
            return None
    finally:
        connection.close()
    return json.loads(row[0])


def _sqlite_set(key: str, payload: Any, ttl_seconds: int) -> None:
    path = _ensure_sqlite()
    encoded = json.dumps(payload, separators=(",", ":"), default=str)
    connection = sqlite3.connect(path, timeout=5)
    try:
        connection.execute(
            """
            INSERT INTO api_cache(cache_key, payload, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                payload = excluded.payload,
                expires_at = excluded.expires_at
            """,
            (key, encoded, time.time() + ttl_seconds),
        )
        connection.execute("DELETE FROM api_cache WHERE expires_at <= ?", (time.time(),))
        connection.commit()
    finally:
        connection.close()


def _upstash_command(command: list[Any]) -> Any:
    config = _upstash_config()
    if not config:
        raise RuntimeError("Upstash cache selected without REST credentials.")
    url, token = config
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json=command,
        timeout=5,
    )
    response.raise_for_status()
    body = response.json()
    if body.get("error"):
        raise RuntimeError(str(body["error"]))
    return body.get("result")


def _upstash_get(key: str) -> Any:
    result = _upstash_command(["GET", key])
    if result is None:
        return None
    return json.loads(result)


def _upstash_set(key: str, payload: Any, ttl_seconds: int) -> None:
    encoded = json.dumps(payload, separators=(",", ":"), default=str)
    _upstash_command(["SET", key, encoded, "EX", max(1, int(ttl_seconds))])


def get_json(key: str) -> Any:
    try:
        backend = _backend_name()
        if backend == "memory":
            return _memory_get(key)
        if backend == "upstash":
            return _upstash_get(key)
        if backend == "sqlite":
            return _sqlite_get(key)
        raise RuntimeError(f"Unsupported CACHE_BACKEND: {backend}")
    except Exception as exc:
        print(f"Cache read failed ({type(exc).__name__}); continuing without cache.", flush=True)
        return None


def set_json(key: str, payload: Any, ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        return
    try:
        backend = _backend_name()
        if backend == "memory":
            _memory_set(key, payload, ttl_seconds)
        elif backend == "upstash":
            _upstash_set(key, payload, ttl_seconds)
        elif backend == "sqlite":
            _sqlite_set(key, payload, ttl_seconds)
        else:
            raise RuntimeError(f"Unsupported CACHE_BACKEND: {backend}")
    except Exception as exc:
        print(f"Cache write failed ({type(exc).__name__}); continuing without cache.", flush=True)
