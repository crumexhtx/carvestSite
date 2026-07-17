import os
import threading
from typing import Optional

import env_setup  # noqa: F401
from openai import OpenAI


class OpenAIConfigurationError(Exception):
    pass


_CLIENT: Optional[OpenAI] = None
_LOCK = threading.Lock()


def get_openai_client() -> OpenAI:
    """Lazily create a shared OpenAI client so non-AI routes can import safely."""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT

    with _LOCK:
        if _CLIENT is not None:
            return _CLIENT
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise OpenAIConfigurationError(
                "OPENAI_API_KEY is not set. AI features are unavailable."
            )
        timeout_seconds = float(os.environ.get("OPENAI_TIMEOUT_SECONDS", "45"))
        max_retries = max(0, int(os.environ.get("OPENAI_MAX_RETRIES", "2")))
        _CLIENT = OpenAI(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )
        return _CLIENT


def create_openai_client() -> OpenAI:
    """Backward-compatible alias for get_openai_client()."""
    return get_openai_client()


class _LazyOpenAIClient:
    """Module-level proxy so existing `client.chat...` call sites stay lazy."""

    def __getattr__(self, name: str):
        return getattr(get_openai_client(), name)


client = _LazyOpenAIClient()
