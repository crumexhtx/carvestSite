import json
import sys
import time
import requests
from urllib.parse import quote

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def save_database(database, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)


def build_vehicle_json_database(filename="vehicles.json", start_year=1995, end_year=2026):
    # Master list of API-compliant brand strings across all major global regions
    target_makes = [
        "ford", "chevrolet", "gmc", "buick", "cadillac", "jeep", "dodge", "ram", "chrysler", "lincoln", "tesla", "rivian", "lucid", "pontiac", "saturn", "hummer", "mercury", "oldsmobile", "plymouth",
        "toyota", "lexus", "honda", "acura", "nissan", "infiniti", "subaru", "mazda", "mitsubishi", "scion",
        "volkswagen", "audi", "bmw", "mercedes-benz", "porsche", "volvo", "land rover", "jaguar", "mini", "fiat", "alfa romeo", "saab",
        "polestar", "byd", "lotus",
        "hyundai", "kia", "genesis"
    ]

    database = {}

    for make in target_makes:
        # Standardize key casing for visual formatting
        display_make = make.title() if make not in ["bmw", "gmc", "byd"] else make.upper()
        database[display_make] = {}

        print(f"--- Starting data collection for: {display_make} ---", flush=True)

        for year in range(start_year, end_year + 1):
            url = (
                "https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMakeYear"
                f"/make/{quote(make)}/modelyear/{year}?format=json"
            )

            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()

                # Clean up individual model strings
                models_this_year = [
                    item["Model_Name"].strip()
                    for item in data.get("Results", [])
                    if item.get("Model_Name")
                ]

                # Strip duplicates and sort alphabetically
                unique_models = sorted(list(set(models_this_year)))

                if unique_models:
                    database[display_make][str(year)] = unique_models
                    print(f"  [{year}]: Saved {len(unique_models)} models", flush=True)

            except requests.exceptions.RequestException as e:
                print(f"  Error fetching {year} {display_make}: {e}", flush=True)

            # Brief pause to respect federal API servers
            time.sleep(0.2)

        save_database(database, filename)
        print(f"Checkpoint saved for {display_make}", flush=True)

    print(f"\nSuccess! Database completely written to '{filename}'", flush=True)


if __name__ == "__main__":
    build_vehicle_json_database()
