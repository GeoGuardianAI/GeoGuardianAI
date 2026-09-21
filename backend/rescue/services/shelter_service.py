"""Shelter service for the Resource & Rescue Management module.

Provides a deterministic in-memory collection of mock shelters and a helper
to find the nearest shelter with emergency availability and open capacity.
"""

from __future__ import annotations

from backend.rescue.models.shelter import EmergencyShelter, Shelter, ShelterStatus
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

_EMERGENCY_SHELTERS: list[EmergencyShelter] = [
    EmergencyShelter(
        shelter_id="shelter-blr-01",
        name="Bengaluru East Community Relief Center",
        latitude=12.9856,
        longitude=77.6050,
        capacity=500,
        available_capacity=220,
        status=ShelterStatus.ACCEPTING_EVACUEES,
    ),
    EmergencyShelter(
        shelter_id="shelter-blr-02",
        name="Bengaluru South Sports Complex Shelter",
        latitude=12.9352,
        longitude=77.6245,
        capacity=350,
        available_capacity=140,
        status=ShelterStatus.ACCEPTING_EVACUEES,
    ),
    EmergencyShelter(
        shelter_id="shelter-blr-03",
        name="Bengaluru North Civic Evacuation Hall",
        latitude=13.0205,
        longitude=77.6400,
        capacity=280,
        available_capacity=0,
        status=ShelterStatus.FULL,
    ),
    EmergencyShelter(
        shelter_id="shelter-blr-04",
        name="Bengaluru West Relief School",
        latitude=12.9568,
        longitude=77.5195,
        capacity=240,
        available_capacity=80,
        status=ShelterStatus.CLOSED,
    ),
]


def get_shelters() -> list[EmergencyShelter]:
    """Return all emergency shelters in registry order."""
    return list(_EMERGENCY_SHELTERS)


def get_available_shelters() -> list[EmergencyShelter]:
    """Return shelters accepting evacuees with open capacity."""
    return [
        shelter
        for shelter in _EMERGENCY_SHELTERS
        if shelter.status in {ShelterStatus.ACCEPTING_EVACUEES, ShelterStatus.AVAILABLE}
        and shelter.available_capacity > 0
    ]


def get_emergency_shelter(shelter_id: str) -> EmergencyShelter:
    """Return an emergency shelter by ID."""
    for shelter in _EMERGENCY_SHELTERS:
        if shelter.shelter_id == shelter_id:
            return shelter
    raise ValueError(f"Emergency shelter '{shelter_id}' does not exist")


def update_available_capacity(shelter_id: str, available_capacity: int) -> EmergencyShelter:
    """Update a shelter's available capacity."""
    shelter = get_emergency_shelter(shelter_id)
    if available_capacity < 0 or available_capacity > shelter.capacity:
        raise ValueError("available_capacity must be between 0 and capacity")
    shelter.available_capacity = available_capacity
    return shelter


def get_nearest_available_emergency_shelter(
    latitude: float, longitude: float
) -> tuple[EmergencyShelter, float]:
    """Return the nearest accepting shelter and its distance in kilometres."""
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError("latitude must be between -90 and 90")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError("longitude must be between -180 and 180")

    available_shelters = get_available_shelters()
    if not available_shelters:
        raise ValueError("no suitable shelter available")

    shelter = min(
        available_shelters,
        key=lambda item: haversine_km(latitude, longitude, item.latitude, item.longitude),
    )
    return shelter, haversine_km(latitude, longitude, shelter.latitude, shelter.longitude)


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