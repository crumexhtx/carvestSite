import os

import env_setup  # noqa: F401
from openai import OpenAI


def create_openai_client() -> OpenAI:
    timeout_seconds = float(os.environ.get("OPENAI_TIMEOUT_SECONDS", "45"))
    max_retries = max(0, int(os.environ.get("OPENAI_MAX_RETRIES", "2")))
    return OpenAI(timeout=timeout_seconds, max_retries=max_retries)
