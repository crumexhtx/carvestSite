from fetch_marketcheck import _request


def get_inventory_scale() -> dict:
    """Lightweight nationwide inventory count from MarketCheck."""
    data = _request(
        "/search/car/active",
        {
            "car_type": "used",
            "rows": 1,
            "photo_links": "false",
            "append_api_key": "false",
        },
    )
    total = int(data.get("num_found") or 0)
    return {
        "total_listings_nationwide": total,
        "label": f"{total:,} active dealer listings nationwide",
    }
