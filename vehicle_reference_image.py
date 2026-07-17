"""Free reference images for assistant cards when MarketCheck photos are unavailable."""

from __future__ import annotations

import os
import re
from typing import Any, Optional
from urllib.parse import quote

import requests

from cache_backend import build_cache_key, get_json, set_json


WIKIPEDIA_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
USER_AGENT = os.environ.get(
    "CARVEST_USER_AGENT",
    "Carvest/1.0 (vehicle research education; contact=support@carvest.local)",
)
TTL_SECONDS = int(os.environ.get("REFERENCE_IMAGE_TTL_SECONDS", "2592000"))  # 30 days
MISSING_TTL_SECONDS = int(os.environ.get("REFERENCE_IMAGE_MISSING_TTL_SECONDS", "900"))
MAX_IMAGE_BYTES = int(os.environ.get("REFERENCE_IMAGE_MAX_BYTES", str(5 * 1024 * 1024)))
# Wikimedia only serves these thumb widths for direct requests (see https://w.wiki/GHai).
_WIKIMEDIA_THUMB_STEPS = (20, 40, 60, 120, 250, 330, 500, 960, 1280, 1920, 3840)
_REFERENCE_IMAGE_WIDTH = int(os.environ.get("REFERENCE_IMAGE_WIDTH", "960"))


def _clean_model(model: str) -> str:
    return re.sub(r"\s+", " ", str(model or "").strip())


def _title_candidates(make: str, model: str, year: Optional[int] = None) -> list[str]:
    make = str(make or "").strip()
    model = _clean_model(model)
    if not make or not model:
        return []

    # Prefer unyear'd model pages first — year-specific Wikipedia pages often 404.
    candidates = [
        f"{make} {model}",
        f"{make}_{model}".replace(" ", "_"),
    ]

    # Common Wikipedia page patterns for hyphenated / spaced models.
    compact = model.replace("-", "").replace(" ", "")
    dashed = model.replace(" ", "-")
    if compact.lower() != model.replace(" ", "").lower():
        candidates.append(f"{make} {compact}")
    if dashed.lower() != model.lower():
        candidates.append(f"{make} {dashed}")

    # Hummer EV pages live under shorter titles than "GMC Hummer EV SUV".
    lowered = model.lower()
    if "hummer ev" in lowered:
        candidates.extend(
            [
                "GMC Hummer EV",
                "Hummer EV",
                "GMC Hummer EV SUV",
                "GMC Hummer EV Pickup",
            ]
        )
    if make.lower() == "gmc" and lowered.startswith("hummer"):
        candidates.append("GMC Hummer EV")

    # Drop body-style suffixes that often 404 on Wikipedia (SUV/Pickup/Sedan).
    for suffix in (" SUV", " Pickup", " Truck", " Sedan", " Coupe"):
        if model.lower().endswith(suffix.lower()):
            shortened = model[: -len(suffix)].strip()
            if shortened:
                candidates.append(f"{make} {shortened}")
                candidates.append(shortened)

    if year:
        candidates.append(f"{year} {make} {model}")

    # Deduplicate while preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for title in candidates:
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(title)
    return ordered


def _wikimedia_thumb_width(desired: int) -> int:
    """Snap to the smallest allowed Wikimedia thumb step at or above desired."""
    for step in _WIKIMEDIA_THUMB_STEPS:
        if step >= desired:
            return step
    return _WIKIMEDIA_THUMB_STEPS[-1]


def _upgrade_wikimedia_url(url: str, desired_width: Optional[int] = None) -> str:
    """Rewrite /NNNpx- thumbnails to a sharper allowed size for UI cards."""
    width = _wikimedia_thumb_width(desired_width or _REFERENCE_IMAGE_WIDTH)
    if re.search(r"/\d+px-", url):
        return re.sub(r"/\d+px-", f"/{width}px-", url, count=1)
    # Full originals under /commons/ (not /thumb/) — leave as-is; proxy will stream them.
    return url


def _wikipedia_thumbnail(title: str) -> tuple[Optional[str], bool]:
    """Return (image_url_or_none, lookup_succeeded).

    lookup_succeeded is False on transport/parse failures so callers can avoid
    caching transient misses for a full day.
    """
    url = WIKIPEDIA_SUMMARY.format(title=quote(title.replace(" ", "_"), safe="_()-"))
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
            timeout=float(os.environ.get("REFERENCE_IMAGE_TIMEOUT_SECONDS", "6")),
        )
        if response.status_code == 404:
            return None, True
        if response.status_code != 200:
            return None, False
        body = response.json()
    except (requests.RequestException, ValueError):
        return None, False

    thumbnail = body.get("thumbnail") or {}
    source = thumbnail.get("source")
    if not source:
        original = body.get("originalimage") or {}
        source = original.get("source")
    if not source or not str(source).startswith("http"):
        return None, True
    return _upgrade_wikimedia_url(str(source)), True


def _imagin_url(make: str, model: str, year: Optional[int]) -> Optional[str]:
    customer = os.environ.get("IMAGIN_CUSTOMER", "").strip()
    if not customer:
        return None
    model_family = re.sub(r"[^a-z0-9]+", "", _clean_model(model).lower())
    if not model_family:
        return None
    params = [
        f"customer={quote(customer)}",
        f"make={quote(make.lower())}",
        f"modelFamily={quote(model_family)}",
        "angle=23",
        "width=800",
        "zoomType=fullscreen",
    ]
    if year:
        params.append(f"modelYear={int(year)}")
    return "https://cdn.imagin.studio/getImage?" + "&".join(params)


def get_reference_image(
    make: str,
    model: str,
    year: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    """Return a free reference image for UI cards. Never raises."""
    cache_key = build_cache_key(
        "vehicle-reference-image:v4",
        {
            "make": make,
            "model": model,
            "year": year,
            "width": _wikimedia_thumb_width(_REFERENCE_IMAGE_WIDTH),
        },
    )
    cached = get_json(cache_key)
    if isinstance(cached, dict):
        if cached.get("missing"):
            return None
        return cached if cached.get("photo") else None

    photo: Optional[str] = None
    source = "wikipedia"
    confirmed_miss = False
    for title in _title_candidates(make, model, year):
        candidate, lookup_ok = _wikipedia_thumbnail(title)
        if candidate:
            photo = candidate
            break
        if lookup_ok:
            confirmed_miss = True

    if not photo:
        imagin = _imagin_url(make, model, year)
        if imagin:
            photo = imagin
            source = "imagin"

    if not photo:
        # Only cache misses after at least one confirmed provider response.
        if confirmed_miss:
            set_json(cache_key, {"missing": True}, min(TTL_SECONDS, MISSING_TTL_SECONDS))
        return None

    payload = {
        "photo": photo,
        "photo_source": "reference",
        "provider": source,
    }
    set_json(cache_key, payload, TTL_SECONDS)
    return payload


def resolve_vehicle_photo(
    listing_photo: Optional[str],
    make: str,
    model: str,
    year: Optional[int] = None,
) -> dict[str, Any]:
    """Prefer MarketCheck listing photos; otherwise attach a free reference image."""
    if listing_photo:
        return {
            "photo": listing_photo,
            "photo_source": "listing",
        }
    reference = get_reference_image(make, model, year)
    if reference:
        return {
            "photo": reference["photo"],
            "photo_source": "reference",
            "provider": reference.get("provider"),
        }
    return {
        "photo": None,
        "photo_source": None,
    }


_ALLOWED_IMAGE_HOSTS = {
    "upload.wikimedia.org",
    "commons.wikimedia.org",
    "cdn.imagin.studio",
}


def fetch_reference_image_bytes(
    make: str,
    model: str,
    year: Optional[int] = None,
) -> tuple[bytes, str]:
    """Download a reference image for same-origin browser display."""
    resolved = resolve_vehicle_photo(None, make, model, year)
    source_url = resolved.get("photo")
    if not source_url:
        raise FileNotFoundError("No reference image found for this vehicle.")

    from urllib.parse import urlparse

    host = (urlparse(str(source_url)).hostname or "").lower()
    if host not in _ALLOWED_IMAGE_HOSTS:
        raise ValueError("Reference image host is not allowed.")

    response = requests.get(
        str(source_url),
        headers={"User-Agent": USER_AGENT, "Accept": "image/*,*/*"},
        timeout=float(os.environ.get("REFERENCE_IMAGE_TIMEOUT_SECONDS", "8")),
        stream=True,
    )
    response.raise_for_status()
    content_length = response.headers.get("Content-Length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_IMAGE_BYTES:
        response.close()
        raise ValueError("Reference image exceeds size limit.")

    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=65536):
        if not chunk:
            continue
        total += len(chunk)
        if total > MAX_IMAGE_BYTES:
            response.close()
            raise ValueError("Reference image exceeds size limit.")
        chunks.append(chunk)
    response.close()

    content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
    if not content_type.startswith("image/"):
        content_type = "image/jpeg"
    return b"".join(chunks), content_type
