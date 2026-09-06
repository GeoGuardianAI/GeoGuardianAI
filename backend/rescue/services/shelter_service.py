"""Shelter service for the Resource & Rescue Management module.

Provides a deterministic in-memory collection of mock shelters and a helper
to find the nearest shelter with emergency availability and open capacity.
"""

from __future__ import annotations

from backend.rescue.models.shelter import Shelter
from backend.rescue.utils.geo import haversine_km


# Deterministic, realistic mock shelters for local testing.
# The list order is used as a stable tie-breaker when distances match.
_SHELTERS: list[Shelter] = [
    Shelter(
        shelter_id="shelter-nyc-01",
        name="Lower Manhattan Community Shelter",
        latitude=40.7128,
        longitude=-74.0060,
        capacity=300,
        occupied=180,
        emergency_available=True,
    ),
    Shelter(
        shelter_id="shelter-la-01",
        name="Los Angeles Civic Relief Center",
        latitude=34.0522,
        longitude=-118.2437,
        capacity=250,
        occupied=250,
        emergency_available=True,
    ),
    Shelter(
        shelter_id="shelter-chi-01",
        name="Chicago Westside Emergency Shelter",
        latitude=41.8781,
        longitude=-87.6298,
        capacity=220,
        occupied=90,
        emergency_available=False,
    ),
    Shelter(
        shelter_id="shelter-hou-01",
        name="Houston Flood Evacuation Shelter",
        latitude=29.7604,
        longitude=-95.3698,
        capacity=400,
        occupied=275,
        emergency_available=True,
    ),
    Shelter(
        shelter_id="shelter-mia-01",
        name="Miami Bay Emergency Shelter",
        latitude=25.7617,
        longitude=-80.1918,
        capacity=180,
        occupied=60,
        emergency_available=True,
    ),
]


def get_nearest_shelter(latitude: float, longitude: float) -> Shelter:
    """Return the nearest suitable shelter to the given coordinates.

    A suitable shelter is accepting emergencies and has at least one
    available space. Ties are resolved by the order of the in-memory list.

    Args:
        latitude: Query latitude in decimal degrees.
        longitude: Query longitude in decimal degrees.

    Raises:
        ValueError: If coordinates are out of range or no suitable shelter is
            available.
    """
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError("latitude must be between -90 and 90")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError("longitude must be between -180 and 180")

    suitable_shelters = [
        shelter
        for shelter in _SHELTERS
        if shelter.emergency_available and shelter.available_spaces > 0
    ]
    if not suitable_shelters:
        raise ValueError("no suitable shelter available")

    return min(
        suitable_shelters,
        key=lambda shelter: haversine_km(
            latitude, longitude, shelter.latitude, shelter.longitude
        ),
    )