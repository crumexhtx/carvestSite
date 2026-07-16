import json
from pathlib import Path
from typing import Any, Optional

MAP_FILE = Path(__file__).parent / "competitor_map.json"


def _normalize_key(make: str, model: str) -> str:
    return f"{make.strip().lower()}|{model.strip().lower()}"


YEAR_MODEL_ALIASES: dict[tuple[str, str], list[tuple[range, str]]] = {
    ("Kia", "K5"): [(range(1990, 2021), "Optima")],
    ("Mazda", "Mazda6"): [(range(1990, 2026), "Mazda6")],
}


def resolve_model_alias(make: str, model: str, year: int) -> str:
    aliases = YEAR_MODEL_ALIASES.get((make, model))
    if not aliases:
        return model

    for years, replacement in aliases:
        if year in years:
            return replacement
    return model


def load_competitor_map(path: Path = MAP_FILE) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def get_competitors(
    make: str,
    model: str,
    exclude_self: bool = True,
    limit: int = 4,
) -> dict[str, Any]:
    data = load_competitor_map()
    key = _normalize_key(make, model)
    entry = data["models"].get(key)

    if entry:
        competitors = list(entry["competitors"])
        segment = entry["segment"]
        source = "model_map"
    else:
        competitors = []
        segment = None
        source = "none"

    if exclude_self:
        competitors = [
            item
            for item in competitors
            if _normalize_key(item["make"], item["model"]) != key
        ]

    return {
        "segment": segment,
        "source": source,
        "competitors": competitors[:limit],
        "people_also_shop": [f"{item['make']} {item['model']}" for item in competitors[:limit]],
    }


def resolve_competitor_models(
    make: str,
    model: str,
    year: int,
    verify_fn,
    limit: int = 4,
) -> list[dict[str, Any]]:
    lookup = get_competitors(make, model, limit=limit)
    resolved = []

    for candidate in lookup["competitors"]:
        resolved_model = resolve_model_alias(candidate["make"], candidate["model"], year)
        is_valid, message, canonical_model = verify_fn(
            candidate["make"],
            year,
            resolved_model,
        )
        if is_valid:
            resolved.append(
                {
                    "make": candidate["make"],
                    "model": canonical_model,
                    "display_model": candidate["model"],
                    "year": year,
                    "verified": True,
                }
            )
        else:
            resolved.append(
                {
                    "make": candidate["make"],
                    "model": resolved_model,
                    "display_model": candidate["model"],
                    "year": year,
                    "verified": False,
                    "error": message,
                }
            )

    return resolved
