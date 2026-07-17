"""Shared email normalization helpers."""

from __future__ import annotations

import re
from typing import Optional


# Practical RFC-ish check: local@domain.tld without spaces or consecutive dots.
_EMAIL_RE = re.compile(
    r"^(?=.{3,254}$)"
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,}$"
)


class EmailValidationError(ValueError):
    pass


def normalize_email(email: str, *, required: bool = True) -> Optional[str]:
    cleaned = str(email or "").strip().lower()
    if not cleaned:
        if required:
            raise EmailValidationError("Enter a valid email address.")
        return None
    if len(cleaned) > 254:
        raise EmailValidationError("Email address is too long.")
    if cleaned.count("@") != 1 or ".." in cleaned or " " in cleaned:
        raise EmailValidationError("Enter a valid email address.")
    if not _EMAIL_RE.fullmatch(cleaned):
        raise EmailValidationError("Enter a valid email address.")
    return cleaned
