"""Curated SEO vehicle hubs and public model briefs for crawlable pages."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from fetch_recalls import get_live_recalls, recalls_available
from home_insights import (
    RECALL_WATCHLIST,
    TOP_RELIABLE_VEHICLES,
    reliability_reference_year,
)

VEHICLES_FILE = Path(__file__).parent / "vehicles.json"

# Marketing / survey names that do not match the VIN catalog exactly.
MODEL_SLUG_ALIASES: dict[tuple[str, str], str] = {
    ("toyota", "corolla-hybrid"): "corolla",
    ("chevrolet", "silverado-1500"): "silverado",
}


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower())
    return cleaned.strip("-")


@lru_cache(maxsize=1)
def _load_vehicle_db() -> dict[str, dict[str, list[str]]]:
    with VEHICLES_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_exact(
    make_slug: str, model_slug: str, year_str: str
) -> tuple[str, str, int] | None:
    db = _load_vehicle_db()
    make_key = None
    for candidate in db.keys():
        if slugify(candidate) == slugify(make_slug):
            make_key = candidate
            break
    if make_key is None:
        return None

    year_models = db[make_key].get(year_str)
    if not year_models:
        return None

    target = slugify(model_slug)
    for model_name in year_models:
        if slugify(model_name) == target:
            return make_key, model_name, int(year_str)
    return None


def resolve_vehicle(make_slug: str, model_slug: str, year: str | int) -> tuple[str, str, int] | None:
    """Map URL slugs to canonical catalog make/model/year, or None if unknown."""
    year_str = str(year).strip()
    if not year_str.isdigit():
        return None
    year_int = int(year_str)
    if year_int < 1981 or year_int > 2100:
        return None

    exact = _resolve_exact(make_slug, model_slug, year_str)
    if exact is not None:
        return exact

    alias = MODEL_SLUG_ALIASES.get((slugify(make_slug), slugify(model_slug)))
    if alias:
        return _resolve_exact(make_slug, alias, year_str)
    return None


def _reliability_note(make: str, model: str) -> str | None:
    make_l = make.strip().lower()
    model_l = model.strip().lower()
    model_slug = slugify(model)
    for item in TOP_RELIABLE_VEHICLES:
        if item["make"].lower() != make_l:
            continue
        item_model = str(item["model"])
        if item_model.lower() == model_l or slugify(item_model) == model_slug:
            return str(item["note"])
        # Catalog may use a shorter base name (Corolla vs Corolla Hybrid).
        if slugify(item_model).startswith(model_slug) or model_slug.startswith(
            slugify(item_model)
        ):
            return str(item["note"])
    return None


def curated_hubs() -> list[dict[str, Any]]:
    """Stable list of high-intent hubs for sitemap and /cars index."""
    year = reliability_reference_year()
    seen: set[tuple[str, str, int]] = set()
    hubs: list[dict[str, Any]] = []

    def _add(make: str, model: str, hub_year: int, *, reason: str, note: str | None = None) -> None:
        key = (make.lower(), model.lower(), hub_year)
        if key in seen:
            return
        resolved = resolve_vehicle(slugify(make), slugify(model), hub_year)
        if resolved is None:
            # Prefer catalog-valid pages only.
            return
        canon_make, canon_model, canon_year = resolved
        seen.add((canon_make.lower(), canon_model.lower(), canon_year))
        hubs.append(
            {
                "make": canon_make,
                "model": canon_model,
                "year": canon_year,
                "make_slug": slugify(canon_make),
                "model_slug": slugify(canon_model),
                "path": f"/cars/{slugify(canon_make)}/{slugify(canon_model)}/{canon_year}",
                "reason": reason,
                "note": note,
                "title": f"{canon_year} {canon_make} {canon_model}",
            }
        )

    for item in TOP_RELIABLE_VEHICLES:
        _add(
            item["make"],
            item["model"],
            year,
            reason="reliability",
            note=str(item.get("note") or ""),
        )

    for item in RECALL_WATCHLIST:
        _add(
            item["make"],
            item["model"],
            int(item["year"]),
            reason="recall_watch",
            note="On Carvest's live NHTSA recall watchlist.",
        )

    hubs.sort(key=lambda row: (row["make"], row["model"], -row["year"]))
    return hubs


def get_model_brief(make_slug: str, model_slug: str, year: str | int) -> dict[str, Any] | None:
    resolved = resolve_vehicle(make_slug, model_slug, year)
    if resolved is None:
        return None

    make, model, year_int = resolved
    recalls = get_live_recalls(make, year_int, model, verbose=False)
    available = recalls_available(recalls)
    recall_rows = []
    if available:
        for item in (recalls.get("recalls_list") or [])[:5]:
            recall_rows.append(
                {
                    "component": item.get("Component") or "Safety recall",
                    "summary": item.get("Summary") or "",
                    "consequence": item.get("Consequence") or "",
                    "remedy": item.get("Remedy") or "",
                }
            )

    note = _reliability_note(make, model)
    research_prompt = (
        f"Tell me about the {year_int} {make} {model} — reliability, "
        "best years to buy, common issues, and what to watch for."
    )

    return {
        "make": make,
        "model": model,
        "year": year_int,
        "make_slug": slugify(make),
        "model_slug": slugify(model),
        "path": f"/cars/{slugify(make)}/{slugify(model)}/{year_int}",
        "title": f"{year_int} {make} {model}",
        "description": (
            f"Research the {year_int} {make} {model}: live NHTSA recalls, "
            "reliability context, and next steps before you buy."
        ),
        "reliability_note": note,
        "research_prompt": research_prompt,
        "recalls": {
            "available": available,
            "total_recalls_count": recalls.get("total_recalls_count"),
            "items": recall_rows,
        },
    }
