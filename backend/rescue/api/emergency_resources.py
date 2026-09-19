from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from backend.rescue.models.emergency_resource import (
    EmergencyResource,
    ResourceAllocationRequest,
    ResourceType,
)
from backend.rescue.models.allocation import ResourceAllocation
from backend.rescue.services import emergency_resource_service
from backend.rescue.services.allocation_service import allocate_resource_to_mission

router = APIRouter()


class MissionResourceAllocationRequest(BaseModel):
    """Request payload for allocating inventory to an existing mission."""

    mission_id: str = Field(..., description="Mission identifier")
    resource_id: str = Field(..., description="Resource identifier")
    quantity: int = Field(..., gt=0, description="Quantity to allocate (> 0)")

    @field_validator("mission_id", "resource_id")
    @classmethod
    def _validate_nonempty_identifier(cls, value: str) -> str:
        """Reject empty or whitespace-only identifiers."""
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value


@router.post(
    "/allocate-resource-inventory",
    response_model=EmergencyResource,
    summary="Allocate emergency resource inventory",
)
def allocate_resource_inventory(request: ResourceAllocationRequest) -> EmergencyResource:
    """Allocate inventory quantity from the requested resource."""
    try:
        return emergency_resource_service.allocate_resource(
            request.resource_id, request.quantity
        )
    except ValueError as exc:
        if str(exc) == "no suitable resource available":
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.post(
    "/allocate-resource-to-mission",
    response_model=ResourceAllocation,
    summary="Allocate emergency resource inventory to a mission",
)
def allocate_resource_to_mission_endpoint(
    request: MissionResourceAllocationRequest,
):
    """Allocate inventory to an existing mission and return its allocation record."""
    try:
        return allocate_resource_to_mission(
            request.mission_id,
            request.resource_id,
            request.quantity,
        )
    except ValueError as exc:
        message = str(exc)
        if "does not exist" in message or message == "no suitable resource available":
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc