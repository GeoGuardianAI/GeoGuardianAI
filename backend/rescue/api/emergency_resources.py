from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.rescue.models.emergency_resource import EmergencyResource, ResourceType
from backend.rescue.services import emergency_resource_service

router = APIRouter()


@router.get(
    "/available-resources",
    response_model=list[EmergencyResource],
    summary="List available emergency resources",
    description=(
        "Return emergency resources with positive inventory, optionally filtered "
        "by resource type."
    ),
)
def available_resources(
    resource_type: ResourceType | None = Query(
        default=None,
        description="Optional emergency resource type filter",
    ),
) -> list[EmergencyResource]:
    """Return available emergency resources from the inventory service."""
    return emergency_resource_service.get_available_resources(resource_type)


@router.get(
    "/nearby-resources",
    response_model=list[EmergencyResource],
    summary="Find nearby emergency resources",
    description=(
        "Return available emergency resources ordered by distance from the "
        "provided latitude and longitude."
    ),
)
def nearby_resources(
    latitude: float = Query(
        ..., ge=-90.0, le=90.0, description="Latitude in decimal degrees between -90 and 90"
    ),
    longitude: float = Query(
        ..., ge=-180.0, le=180.0, description="Longitude in decimal degrees between -180 and 180"
    ),
    resource_type: ResourceType | None = Query(
        default=None,
        description="Optional emergency resource type filter",
    ),
) -> list[EmergencyResource]:
    """Return nearby available resources using the inventory service."""
    try:
        return emergency_resource_service.get_nearby_resources(
            latitude, longitude, resource_type
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc