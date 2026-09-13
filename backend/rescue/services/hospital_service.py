"""Hospital service for the Resource & Rescue Management module.

Provides a deterministic in-memory collection of mock hospitals and a
helper to find the nearest hospital to given coordinates using the
Haversine formula.

This module is intentionally simple and has no external dependencies
or persistence; it will be replaced or extended with database-backed
implementations later.
"""

from __future__ import annotations

from typing import List

from backend.rescue.models.hospital import Hospital
from backend.rescue.utils.geo import haversine_km


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Backward-compatible wrapper for the shared Haversine distance helper."""
    return haversine_km(lat1, lon1, lat2, lon2)


# Deterministic, realistic mock hospitals in and around Bengaluru for local testing.
# Keep these definitions module-level so they are easy to inspect/test.
_HOSPITALS: List[Hospital] = [
    Hospital(
        hospital_id="blr-central-test",
        name="Bengaluru Central Care Hospital (Mock)",
        latitude=12.9716,
        longitude=77.5946,
        bed_capacity=500,
        available_beds=120,
        icu_capacity=50,
        available_icu=12,
        emergency_available=True,
    ),
    Hospital(
        hospital_id="blr-whitefield-test",
        name="Whitefield Community Medical Center (Mock)",
        latitude=12.9698,
        longitude=77.7499,
        bed_capacity=350,
        available_beds=18,
        icu_capacity=35,
        available_icu=2,
        emergency_available=True,
    ),
    Hospital(
        hospital_id="blr-yelahanka-test",
        name="Yelahanka District Hospital (Mock)",
        latitude=13.1007,
        longitude=77.5963,
        bed_capacity=220,
        available_beds=0,
        icu_capacity=20,
        available_icu=0,
        emergency_available=True,
    ),
    Hospital(
        hospital_id="blr-electronic-city-test",
        name="Electronic City Trauma Centre (Mock)",
        latitude=12.8452,
        longitude=77.6602,
        bed_capacity=280,
        available_beds=64,
        icu_capacity=28,
        available_icu=7,
        emergency_available=False,
    ),
    Hospital(
        hospital_id="blr-rajajinagar-test",
        name="Rajajinagar Health and Trauma Unit (Mock)",
        latitude=13.0108,
        longitude=77.5548,
        bed_capacity=200,
        available_beds=42,
        icu_capacity=20,
        available_icu=4,
        emergency_available=True,
    ),
]


def get_nearest_hospital(latitude: float, longitude: float) -> Hospital:
    """Return the nearest Hospital to the given coordinates.

    Validates that `latitude` is between -90 and 90 and `longitude` is
    between -180 and 180. Computes geographic distance using the
    Haversine formula and returns the Hospital with the smallest
    distance. Ties are resolved deterministically by the order of the
    in-memory list.

    Args:
        latitude: Query latitude in decimal degrees.
        longitude: Query longitude in decimal degrees.

    Raises:
        ValueError: If latitude or longitude are out of their valid ranges.

    Returns:
        The nearest `Hospital` instance from the in-memory collection.
    """
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError("latitude must be between -90 and 90")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError("longitude must be between -180 and 180")

    # find the hospital with the minimum Haversine distance
    nearest = min(
        _HOSPITALS,
        key=lambda h: haversine_km(latitude, longitude, h.latitude, h.longitude),
    )
    return nearest
