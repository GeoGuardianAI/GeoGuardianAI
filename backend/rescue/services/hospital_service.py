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


# Deterministic, realistic mock hospitals (U.S. cities) for local testing.
# Keep these definitions module-level so they are easy to inspect/test.
_HOSPITALS: List[Hospital] = [
    Hospital(
        hospital_id="nyc-central",
        name="New York Central Hospital",
        latitude=40.7128,
        longitude=-74.0060,
        bed_capacity=500,
        available_beds=50,
        icu_capacity=50,
        available_icu=5,
        emergency_available=True,
    ),
    Hospital(
        hospital_id="la-metro",
        name="Los Angeles Metro Medical",
        latitude=34.0522,
        longitude=-118.2437,
        bed_capacity=450,
        available_beds=75,
        icu_capacity=40,
        available_icu=4,
        emergency_available=True,
    ),
    Hospital(
        hospital_id="chi-general",
        name="Chicago General Hospital",
        latitude=41.8781,
        longitude=-87.6298,
        bed_capacity=300,
        available_beds=30,
        icu_capacity=30,
        available_icu=2,
        emergency_available=True,
    ),
    Hospital(
        hospital_id="hou-regional",
        name="Houston Regional Medical Center",
        latitude=29.7604,
        longitude=-95.3698,
        bed_capacity=250,
        available_beds=20,
        icu_capacity=25,
        available_icu=1,
        emergency_available=False,
    ),
    Hospital(
        hospital_id="mia-health",
        name="Miami Health and Trauma",
        latitude=25.7617,
        longitude=-80.1918,
        bed_capacity=200,
        available_beds=60,
        icu_capacity=20,
        available_icu=3,
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
