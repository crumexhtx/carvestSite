import os
import re
from typing import Any

import requests

from cache_backend import build_cache_key, get_json, set_json


VPIC_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues"
VIN_PATTERN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")


class VinDecodeError(Exception):
    pass


def normalize_vin(vin: str) -> str:
    normalized = re.sub(r"[\s-]+", "", str(vin).upper())
    if not VIN_PATTERN.fullmatch(normalized):
        raise VinDecodeError("Enter a valid 17-character VIN.")
    return normalized


def decode_vin(vin: str) -> dict[str, Any]:
    normalized = normalize_vin(vin)
    cache_key = build_cache_key("nhtsa:vin:v2", {"vin": normalized})
    cached = get_json(cache_key)
    if isinstance(cached, dict):
        return cached

    try:
        response = requests.get(
            f"{VPIC_URL}/{normalized}",
            params={"format": "json"},
            timeout=float(os.environ.get("NHTSA_VIN_TIMEOUT_SECONDS", "10")),
        )
        response.raise_for_status()
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise VinDecodeError(f"Could not decode this VIN: {exc}") from exc

    results = body.get("Results") or []
    if not results:
        raise VinDecodeError("NHTSA did not return vehicle details for this VIN.")

    raw = results[0]
    make = str(raw.get("Make") or "").strip()
    model = str(raw.get("Model") or "").strip()
    year_text = str(raw.get("ModelYear") or "").strip()
    if not make or not model or not year_text.isdigit():
        message = str(raw.get("ErrorText") or "The VIN could not be decoded.").strip()
        raise VinDecodeError(message)

    cylinders = str(raw.get("EngineCylinders") or "").strip()
    displacement = str(raw.get("DisplacementL") or "").strip()
    engine_parts = []
    if cylinders:
        engine_parts.append(f"{cylinders} cyl")
    if displacement:
        try:
            engine_parts.append(f"{float(displacement):.1f}L")
        except ValueError:
            engine_parts.append(f"{displacement}L")
    engine_model = str(raw.get("EngineModel") or "").strip()
    if engine_model:
        engine_parts.append(engine_model)
    decoded = {
        "vin": normalized,
        "make": make.title(),
        "model": model,
        "year": int(year_text),
        "trim": str(raw.get("Trim") or "").strip() or None,
        "series": str(raw.get("Series") or "").strip() or None,
        "body_class": str(raw.get("BodyClass") or "").strip() or None,
        "drive_type": str(raw.get("DriveType") or "").strip() or None,
        "fuel_type": str(raw.get("FuelTypePrimary") or "").strip() or None,
        "engine": " · ".join(part for part in engine_parts if part) or None,
        "manufacturer": str(raw.get("Manufacturer") or "").strip() or None,
    }
    set_json(
        cache_key,
        decoded,
        int(os.environ.get("NHTSA_VIN_TTL_SECONDS", "2592000")),
    )
    return decoded
