import os
import threading
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from cache_backend import upstash_command, upstash_configured


EXPENSIVE_PATHS = {
    "/api/assistant/chat",
    "/api/buyer-reports/preview",
    "/api/compare",
    "/api/listing-deal/evaluate",
    "/api/negotiation",
    "/api/offer-sheet/analyze",
    "/api/report",
    "/api/search/criteria",
    "/api/search/listings",
}


class ApiRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.limit = max(1, int(os.environ.get("API_RATE_LIMIT_REQUESTS", "30")))
        self.window_seconds = max(
            1,
            int(os.environ.get("API_RATE_LIMIT_WINDOW_SECONDS", "60")),
        )
        self.enabled = (
            os.environ.get("API_RATE_LIMIT_ENABLED", "true").strip().lower()
            in {"1", "true", "yes"}
        )
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        prefer = os.environ.get("API_RATE_LIMIT_BACKEND", "auto").strip().lower()
        self._use_upstash = prefer == "upstash" or (
            prefer == "auto" and upstash_configured()
        )

    def _client_key(self, request: Request) -> str:
        # Prefer the first X-Forwarded-For hop when running behind a reverse proxy.
        forwarded = request.headers.get("x-forwarded-for", "").strip()
        if forwarded:
            client_host = forwarded.split(",")[0].strip() or "unknown"
        else:
            client_host = request.client.host if request.client else "unknown"
        return f"{client_host}:{request.url.path}"

    def _allow_memory(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - timestamps[0])))
                return False, retry_after
            timestamps.append(now)
            return True, 0

    def _allow_upstash(self, key: str) -> Optional[tuple[bool, int]]:
        """Fixed-window counter in Upstash. Returns None to fall back to memory."""
        try:
            window_id = int(time.time() // self.window_seconds)
            redis_key = f"carvest:ratelimit:{key}:{window_id}"
            count = int(upstash_command(["INCR", redis_key]) or 0)
            if count == 1:
                upstash_command(["EXPIRE", redis_key, self.window_seconds])
            if count > self.limit:
                retry_after = self.window_seconds - int(time.time() % self.window_seconds)
                return False, max(1, retry_after)
            return True, 0
        except Exception as exc:
            print(
                f"Distributed rate limit unavailable ({type(exc).__name__}); "
                "falling back to in-memory limiter.",
                flush=True,
            )
            return None

    def _allow(self, key: str) -> tuple[bool, int]:
        if self._use_upstash:
            distributed = self._allow_upstash(key)
            if distributed is not None:
                return distributed
        return self._allow_memory(key)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        is_expensive = request.url.path in EXPENSIVE_PATHS or (
            request.method == "POST"
            and request.url.path.startswith("/api/buyer-reports/")
        )
        if (
            not self.enabled
            or request.method == "OPTIONS"
            or not is_expensive
        ):
            return await call_next(request)

        allowed, retry_after = self._allow(self._client_key(request))
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again shortly."},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
