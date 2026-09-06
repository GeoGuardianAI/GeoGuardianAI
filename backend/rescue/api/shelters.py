from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.rescue.models.shelter import Shelter
from backend.rescue.services.shelter_service import get_nearest_shelter

router = APIRouter()


@router.get(
    "/nearest-shelter",
    response_model=Shelter,
    summary="Find the nearest suitable shelter",
    description=(
        "Return the nearest emergency shelter with available capacity to the "
        "provided latitude and longitude using the shelter service."
    ),
)
def nearest_shelter(
    latitude: float = Query(
        ..., ge=-90.0, le=90.0, description="Latitude in decimal degrees between -90 and 90"
    ),
    longitude: float = Query(
        ..., ge=-180.0, le=180.0, description="Longitude in decimal degrees between -180 and 180"
    ),
) -> Shelter:
    """Return the nearest suitable shelter for the requested coordinates."""
    try:
        return get_nearest_shelter(latitude, longitude)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc