from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.rescue.models.rescue_team import RescueTeam
from backend.rescue.services.rescue_team_service import get_available_teams

router = APIRouter()


@router.get(
    "/available-team",
    response_model=list[RescueTeam],
    summary="Find available rescue teams",
    description=(
        "Return rescue teams that are currently available and match the optional "
        "specialization filter, ordered by proximity to the requested coordinates."
    ),
)
def available_teams(
    latitude: float = Query(
        ..., ge=-90.0, le=90.0, description="Latitude in decimal degrees between -90 and 90"
    ),
    longitude: float = Query(
        ..., ge=-180.0, le=180.0, description="Longitude in decimal degrees between -180 and 180"
    ),
    specialization: str | None = Query(
        default=None,
        description="Optional specialization to filter available rescue teams by skill or specialty",
    ),
) -> list[RescueTeam]:
    """Return rescue teams available near the supplied coordinates."""
    try:
        return get_available_teams(latitude=latitude, longitude=longitude, specialization=specialization)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
