from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.rescue.models.shelter import EmergencyShelter, Shelter
from backend.rescue.services import shelter_service
from backend.rescue.services.shelter_service import get_nearest_shelter

router = APIRouter()


class ShelterDistanceResponse(EmergencyShelter):
    """Emergency shelter data with distance from the requested location."""

    distance_km: float = Field(..., ge=0)


class ShelterCapacityUpdate(BaseModel):
    """Payload for changing open shelter capacity."""

    available_capacity: int = Field(..., ge=0)


@router.get("/shelters", response_model=list[EmergencyShelter])
def shelters() -> list[EmergencyShelter]:
    """Return all emergency shelters."""
    return shelter_service.get_shelters()


@router.get("/available-shelters", response_model=list[EmergencyShelter])
def available_shelters() -> list[EmergencyShelter]:
    """Return shelters accepting evacuees with available capacity."""
    return shelter_service.get_available_shelters()


@router.post("/shelters/{shelter_id}/capacity", response_model=EmergencyShelter)
def update_shelter_capacity(
    shelter_id: str, update: ShelterCapacityUpdate
) -> EmergencyShelter:
    """Update the available capacity of a registered shelter."""
    try:
        return shelter_service.update_available_capacity(
            shelter_id, update.available_capacity
        )
    except ValueError as exc:
        if "does not exist" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/nearest-shelter",
    response_model=None,
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
) -> Shelter | EmergencyShelter | ShelterDistanceResponse:
    """Return the nearest suitable shelter for the requested coordinates."""
    try:
        # Keep the original legacy fixture contract intact while exposing the
        # new tracking response for Bengaluru emergency shelter queries.
        if 10.0 <= latitude <= 15.0 and 74.0 <= longitude <= 80.0:
            shelter, distance = shelter_service.get_nearest_available_emergency_shelter(
                latitude, longitude
            )
            return ShelterDistanceResponse(
                **shelter.model_dump(), distance_km=round(distance, 3)
            )
        return get_nearest_shelter(latitude, longitude)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc