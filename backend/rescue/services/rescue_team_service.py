"""Service for rescue-team lookup in the Resource & Rescue Management module.

This module provides a deterministic in-memory collection of mock rescue teams
and helper logic to search for teams based on coordinates and specialization.
It intentionally keeps business logic in the service layer and avoids any API,
DB, or routing concerns.
"""

from __future__ import annotations

from backend.rescue.models.rescue_team import Availability, RescueTeam, TeamType
from backend.rescue.utils.geo import haversine_km


# Deterministic, realistic mock rescue teams for local testing.
# The list order is used as a stable tie-breaker when distances match.
_RESCUE_TEAMS: list[RescueTeam] = [
    RescueTeam(
        team_id="rescue-ny-01",
        name="New York Mountain Rescue",
        team_type=TeamType.SEARCH_AND_RESCUE,
        latitude=40.7128,
        longitude=-74.0060,
        members=12,
        specialization=["mountain rescue", "technical climbing", "search"],
        availability=Availability.AVAILABLE,
        current_mission_id=None,
    ),
    RescueTeam(
        team_id="rescue-la-01",
        name="Los Angeles Fire Response Unit",
        team_type=TeamType.FIRE_AND_RESCUE,
        latitude=34.0522,
        longitude=-118.2437,
        members=18,
        specialization=["structure fire", "wildland fire", "evacuation"],
        availability=Availability.AVAILABLE,
        current_mission_id=None,
    ),
    RescueTeam(
        team_id="rescue-chi-01",
        name="Chicago Urban Medical Team",
        team_type=TeamType.MEDICAL,
        latitude=41.8781,
        longitude=-87.6298,
        members=14,
        specialization=["triage", "medical transport", "mass casualty"],
        availability=Availability.AVAILABLE,
        current_mission_id=None,
    ),
    RescueTeam(
        team_id="rescue-hou-01",
        name="Houston Flood Recovery Crew",
        team_type=TeamType.WATER_RESCUE,
        latitude=29.7604,
        longitude=-95.3698,
        members=16,
        specialization=["swift water", "flood rescue", "boat operations"],
        availability=Availability.ASSIGNED,
        current_mission_id="mission-2001",
    ),
    RescueTeam(
        team_id="rescue-miami-01",
        name="Miami Disaster Response Group",
        team_type=TeamType.DISASTER_RESPONSE,
        latitude=25.7617,
        longitude=-80.1918,
        members=20,
        specialization=["disaster response", "logistics", "search"],
        availability=Availability.AVAILABLE,
        current_mission_id=None,
    ),
    RescueTeam(
        team_id="rescue-sea-01",
        name="Seattle Coastal Rescue Team",
        team_type=TeamType.WATER_RESCUE,
        latitude=47.6062,
        longitude=-122.3321,
        members=10,
        specialization=["water rescue", "coastal rescue", "hazmat support"],
        availability=Availability.DEPLOYED,
        current_mission_id="mission-3007",
    ),
    RescueTeam(
        team_id="rescue-den-01",
        name="Denver Wildfire Support Team",
        team_type=TeamType.FIRE_AND_RESCUE,
        latitude=39.7392,
        longitude=-104.9903,
        members=9,
        specialization=["wildland fire", "air support", "evacuation"],
        availability=Availability.UNAVAILABLE,
        current_mission_id="mission-4402",
    ),
]


def get_available_teams(
    latitude: float,
    longitude: float,
    specialization: str | None = None,
) -> list[RescueTeam]:
    """Return all currently available rescue teams ordered by proximity.

    Only teams with `Availability.AVAILABLE` are eligible. If a specialization
    is supplied, the team must include that specialization in its `specialization`
    list. Results are sorted by Haversine distance from the provided coordinates,
    with the in-memory list order preserved as a deterministic tie-breaker.

    Args:
        latitude: Requested latitude in decimal degrees.
        longitude: Requested longitude in decimal degrees.
        specialization: Optional specialization filter.

    Raises:
        ValueError: If latitude or longitude are outside valid geographic bounds.

    Returns:
        A list of `RescueTeam` objects in ascending distance order.
    """
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError("latitude must be between -90 and 90")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError("longitude must be between -180 and 180")

    available_teams = [
        team for team in _RESCUE_TEAMS if team.availability == Availability.AVAILABLE
    ]

    if specialization is not None:
        requested_specialization = specialization.strip().lower()
        available_teams = [
            team
            for team in available_teams
            if any(item.strip().lower() == requested_specialization for item in team.specialization)
        ]

    return sorted(
        available_teams,
        key=lambda team: haversine_km(latitude, longitude, team.latitude, team.longitude),
    )
