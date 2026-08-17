"""Deterministic resource recommendation engine for disaster response.

This module selects the nearest suitable hospital and ranks available rescue teams
using transparent weighted scoring. It is intentionally deterministic and does not
include persistence, APIs, or machine-learning logic.
"""

from __future__ import annotations

from backend.rescue.models.allocation import AllocationRecommendation, AllocationRequest
from backend.rescue.models.hospital import Hospital
from backend.rescue.models.rescue_team import Availability, RescueTeam
from backend.rescue.services.hospital_service import get_nearest_hospital
from backend.rescue.services.rescue_team_service import get_available_teams
from backend.rescue.utils.geo import haversine_km

DISTANCE_WEIGHT = 0.45
SPECIALIZATION_WEIGHT = 0.30
TEAM_CAPACITY_WEIGHT = 0.10
AVAILABILITY_WEIGHT = 0.15
SEVERITY_WEIGHT = 0.15
CAPACITY_WEIGHT = TEAM_CAPACITY_WEIGHT
MAX_TEAM_CAPACITY_FOR_SCORING = 25.0


class ResourceAllocationError(ValueError):
    """Domain-level error raised when no suitable resource can be recommended."""


class NoSuitableHospitalError(ResourceAllocationError):
    """Raised when no suitable hospital is available for the disaster coordinates."""


class NoSuitableRescueTeamError(ResourceAllocationError):
    """Raised when no suitable rescue team is available for the allocation request."""


def _score_team(team: RescueTeam, request: AllocationRequest) -> tuple[float, float]:
    """Return the weighted score and geographic distance for a rescue team candidate."""
    distance_km = haversine_km(request.latitude, request.longitude, team.latitude, team.longitude)

    distance_score = max(0.0, 1.0 - (distance_km / 1000.0))
    availability_score = 1.0 if team.availability == Availability.AVAILABLE else 0.0

    specialization_match = 1.0
    if request.required_specialization is not None:
        requested_specialization = request.required_specialization.strip().lower()
        specialization_match = (
            1.0
            if any(item.strip().lower() == requested_specialization for item in team.specialization)
            else 0.0
        )

    capacity_score = min(1.0, team.members / MAX_TEAM_CAPACITY_FOR_SCORING)

    score = (
        DISTANCE_WEIGHT * distance_score
        + SPECIALIZATION_WEIGHT * specialization_match
        + AVAILABILITY_WEIGHT * availability_score
        + TEAM_CAPACITY_WEIGHT * capacity_score
    )
    score *= 1.0 + (request.severity - 1) * SEVERITY_WEIGHT

    return score, distance_km


def recommend_resources(request: AllocationRequest) -> AllocationRecommendation:
    """Return a deterministic recommendation for the nearest hospital and best team.

    The hospital is selected as the nearest hospital to the disaster coordinates.
    The rescue team is selected from the available teams, optionally filtered by the
    required specialization, and ranked by a transparent weighted score based on:
    proximity, specialization match, availability, team capacity, and disaster severity.
    """
    try:
        hospital = get_nearest_hospital(request.latitude, request.longitude)
    except ValueError as exc:
        raise NoSuitableHospitalError(
            f"No suitable hospital found for coordinates ({request.latitude}, {request.longitude})."
        ) from exc

    matched_teams = get_available_teams(
        latitude=request.latitude,
        longitude=request.longitude,
        specialization=request.required_specialization,
    )

    if not matched_teams:
        raise NoSuitableRescueTeamError(
            "No suitable rescue team exists for the requested disaster coordinates and specialization."
        )

    scored_teams = [(team, *_score_team(team, request)) for team in matched_teams]
    best_team, score, distance_km = sorted(
        scored_teams,
        key=lambda item: (-item[1], item[2], item[0].team_id),
    )[0]

    priority_score = min(100.0, max(0.0, score * 100.0))
    reasoning_parts = [
        f"Nearest hospital is {hospital.name} ({hospital.hospital_id}).",
        f"Recommended rescue team is {best_team.name} ({best_team.team_id}).",
        (
            f"Estimated team distance is {distance_km:.1f} km and request severity is "
            f"{request.severity}/5."
        ),
    ]
    if request.required_specialization:
        reasoning_parts.append(
            f"Team matches required specialization '{request.required_specialization}'."
        )

    return AllocationRecommendation(
        disaster_id=request.disaster_id,
        recommended_hospital=hospital,
        recommended_rescue_team=best_team,
        priority_score=round(priority_score, 2),
        reasoning=" ".join(reasoning_parts),
        estimated_distance_km=round(distance_km, 2),
    )
