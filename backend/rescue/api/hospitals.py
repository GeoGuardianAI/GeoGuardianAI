from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.rescue.models.hospital import Hospital
from backend.rescue.services.hospital_service import get_nearest_hospital

router = APIRouter()


@router.get(
    "/nearest-hospital",
    response_model=Hospital,
    summary="Find the nearest hospital",
    description="Return the nearest hospital to the provided latitude and longitude using the hospital service.",
)
def nearest_hospital(
    latitude: float = Query(
        ..., ge=-90.0, le=90.0, description="Latitude in decimal degrees between -90 and 90"
    ),
    longitude: float = Query(
        ..., ge=-180.0, le=180.0, description="Longitude in decimal degrees between -180 and 180"
    ),
) -> Hospital:
    """Return the nearest hospital for the requested geographic coordinates."""
    try:
        return get_nearest_hospital(latitude, longitude)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
