"""Launch feature flags for soft-launch vs monetized rollout."""

import os
from typing import Optional


def _truthy(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def monetization_enabled() -> bool:
    """When false, paid VIN reports and checkout stay offline for the soft launch."""
    return _truthy(os.environ.get("MONETIZATION_ENABLED"), default=False)


def waitlist_enabled() -> bool:
    """Collect emails for paid-report launch notifications."""
    return _truthy(os.environ.get("WAITLIST_ENABLED"), default=True)


def public_feature_flags() -> dict[str, bool]:
    return {
        "monetization_enabled": monetization_enabled(),
        "waitlist_enabled": waitlist_enabled(),
    }
