import json
import sys
from pathlib import Path

import env_setup  # noqa: F401
from app_ai_core import generate_ai_vehicle_report, verify_vehicle_exists
from compare_vehicles import run_comparison

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_SAMPLE = Path(__file__).parent / "exampleCr.json"


def load_vehicle_profile(path: Path = DEFAULT_SAMPLE) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def run_report(profile_path: Path = DEFAULT_SAMPLE) -> str:
    profile = load_vehicle_profile(profile_path)

    make = profile["make"]
    year = int(profile["year"])
    model = profile["model"]
    zip_code = profile.get("zip_code")

    is_valid, message, canonical_model = verify_vehicle_exists(make, year, model)
    if not is_valid:
        raise ValueError(message)

    return generate_ai_vehicle_report(
        make=make,
        year=year,
        model=canonical_model,
        zip_code=zip_code,
        vehicle_profile=profile,
    )


if __name__ == "__main__":
    args = [arg for arg in sys.argv[1:] if arg != "--compare"]
    compare_mode = "--compare" in sys.argv
    sample = args[0] if args else str(DEFAULT_SAMPLE)
    print(f"\nCarvest: running {'comparison' if compare_mode else 'report'} for {sample}\n")

    try:
        if compare_mode:
            report = run_comparison(Path(sample))
            title = "=== CARVEST COMPARISON REPORT ==="
        else:
            report = run_report(Path(sample))
            title = "=== CARVEST BUYER REPORT ==="

        print(title)
        print(report)
        print("============================\n")
    except Exception as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc
