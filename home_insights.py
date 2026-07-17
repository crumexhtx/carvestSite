from datetime import date

from fetch_recalls import get_live_recalls, get_live_recalls_many


def reliability_reference_year() -> int:
    return date.today().year - 3


# Kept for backward compatibility with imports/tests.
RELIABILITY_REFERENCE_YEAR = reliability_reference_year()

# Curated from Consumer Reports owner-reliability surveys (model-year rankings).
TOP_RELIABLE_VEHICLES = [
    {
        "rank": 1,
        "make": "Lexus",
        "model": "GX",
        "note": "Top-rated luxury SUV with consistently low problem rates.",
    },
    {
        "rank": 2,
        "make": "Toyota",
        "model": "Corolla Hybrid",
        "note": "Excellent fuel economy with proven hybrid durability.",
    },
    {
        "rank": 3,
        "make": "Mazda",
        "model": "CX-30",
        "note": "Compact SUV with strong owner satisfaction and few issues.",
    },
    {
        "rank": 4,
        "make": "Toyota",
        "model": "Prius",
        "note": "Hybrid icon with low maintenance costs over the long run.",
    },
    {
        "rank": 5,
        "make": "Honda",
        "model": "Civic",
        "note": "Dependable compact with affordable ownership costs.",
    },
]

TOP_RELIABLE_BRANDS = [
    {"rank": 1, "brand": "Lexus", "note": "Luxury leader with the fewest reported problems."},
    {"rank": 2, "brand": "Toyota", "note": "Benchmark for long-term durability across segments."},
    {"rank": 3, "brand": "Mazda", "note": "Strong reliability with engaging driving dynamics."},
    {"rank": 4, "brand": "Subaru", "note": "All-wheel-drive specialist with loyal owner scores."},
    {"rank": 5, "brand": "Honda", "note": "Consistent quality in sedans, SUVs, and hybrids."},
]

RECALL_WATCHLIST = [
    {"make": "Ford", "model": "F-150", "year": 2024},
    {"make": "Toyota", "model": "Tacoma", "year": 2023},
    {"make": "Tesla", "model": "Model 3", "year": 2024},
    {"make": "Hyundai", "model": "Palisade", "year": 2023},
    {"make": "Chevrolet", "model": "Silverado 1500", "year": 2022},
    {"make": "Honda", "model": "CR-V", "year": 2023},
]

RELIABILITY_REPORTS = [
    {
        "title": "Who Makes the Most Reliable New Cars?",
        "summary": "Consumer Reports’ latest owner survey places Lexus, Subaru, and Toyota at the top, while Tesla improves and Mazda falls.",
        "url": "https://www.consumerreports.org/cars/car-reliability-owner-satisfaction/who-makes-the-most-reliable-cars-a7824554938/",
        "source": "Consumer Reports",
    },
    {
        "title": "Most Reliable Used Cars",
        "summary": "CarMax highlights reliable used vehicles using RepairPal ratings based on the cost, frequency, and severity of unscheduled repairs.",
        "url": "https://www.carmax.com/research/most-reliable-cars",
        "source": "CarMax Research",
    },
    {
        "title": "10 Best Safe, Reliable, and Affordable Cars in America 2026",
        "summary": "A driver-education provider’s 2026 roundup of affordable vehicles recognized for reliability, safety equipment, and ownership value.",
        "url": "https://nhsa.com/en/10-best-safe-reliable-and-affordable-cars-in-america-2026",
        "source": "NHSA Online Drivers Ed · Non-government",
    },
]


def _truncate(text: str, limit: int = 160) -> str:
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _vehicle_reliability_prompt(make: str, model: str, year: int) -> str:
    return (
        f"Tell me about the {year} {make} {model} — reliability, "
        "best years to buy, and what to watch for."
    )


def _brand_reliability_prompt(brand: str) -> str:
    return (
        f"What makes {brand} one of the most reliable brands? "
        f"Which {brand} models should I consider for a used purchase?"
    )


def get_reliability_rankings() -> dict:
    year = reliability_reference_year()
    vehicles = []
    for item in TOP_RELIABLE_VEHICLES:
        make = item["make"]
        model = item["model"]
        vehicles.append(
            {
                "rank": item["rank"],
                "make": make,
                "model": model,
                "year": year,
                "note": item["note"],
                "prompt": _vehicle_reliability_prompt(make, model, year),
            }
        )

    brands = []
    for item in TOP_RELIABLE_BRANDS:
        brand = item["brand"]
        brands.append(
            {
                "rank": item["rank"],
                "brand": brand,
                "note": item["note"],
                "prompt": _brand_reliability_prompt(brand),
            }
        )

    return {
        "reference_year": year,
        "top_vehicles": vehicles,
        "top_brands": brands,
        "source": "Consumer Reports owner-reliability surveys",
    }


def get_home_insights() -> dict:
    recall_requests = [
        (vehicle["make"], vehicle["year"], vehicle["model"])
        for vehicle in RECALL_WATCHLIST
    ]
    recall_results = get_live_recalls_many(
        recall_requests,
        max_workers=3,
        overall_timeout=10,
        verbose=False,
    )

    snippets = []
    for recalls in recall_results:
        if recalls.get("error") or not recalls.get("recalls_list"):
            continue

        first = recalls["recalls_list"][0]
        snippets.append(
            {
                "vehicle": f"{recalls['year']} {recalls['make']} {recalls['model']}",
                "component": first.get("Component", "Safety recall"),
                "summary": _truncate(first.get("Summary", "")),
                "recall_count": recalls.get("total_recalls_count", 0),
            }
        )
        if len(snippets) >= 3:
            break

    if not snippets:
        snippets = [
            {
                "vehicle": "2024 Ford F-150",
                "component": "Recall monitoring active",
                "summary": "Carvest is connected to live NHTSA recall data. Search a specific make and model for the latest safety campaigns.",
                "recall_count": 0,
            }
        ]

    return {
        "recall_snippets": snippets,
        "reliability_article": RELIABILITY_REPORTS[0],
        "reliability_reports": RELIABILITY_REPORTS,
        "reliability_rankings": get_reliability_rankings(),
    }
