from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.rescue.models.mission import Mission, MissionPriority, MissionStatus
from backend.rescue.services.mission_service import (
    create_mission,
    get_mission,
    list_missions,
    update_mission_status,
)

router = APIRouter()


class MissionCreateRequest(BaseModel):
    """Request payload for creating a rescue mission."""

    team_id: str = Field(..., description="Assigned rescue team identifier")
    disaster_id: str = Field(..., description="Disaster event associated with the mission")
    destination_latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Destination latitude in decimal degrees (-90 to 90)",
    )
    destination_longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Destination longitude in decimal degrees (-180 to 180)",
    )
    priority: MissionPriority = Field(
        default=MissionPriority.MEDIUM,
        description="Operational priority of the mission",
    )
    hospital_id: str | None = Field(
        default=None,
        description="Associated hospital identifier, if applicable",
    )
    vehicle_id: str | None = Field(
        default=None,
        description="Assigned vehicle identifier, if applicable",
    )


class MissionStatusUpdateRequest(BaseModel):
    """Request payload for updating a rescue mission status."""

    status: MissionStatus = Field(..., description="New lifecycle status for the mission")


@router.get(
    "/missions",
    response_model=list[Mission],
    summary="List rescue missions",
    tags=["Missions"],
)
def list_missions_endpoint() -> list[Mission]:
    """Return all stored rescue missions."""
    return list_missions()


@router.post(
    "/mission",
    response_model=Mission,
    status_code=status.HTTP_201_CREATED,
    summary="Create a rescue mission",
    description=(
        "Create a mission for an available rescue team and persist it in the in-memory "
        "mission service. The service assigns the team and the mission receives its default "
        "ASSIGNED lifecycle status."
    ),
    response_description="The created mission record.",
    tags=["Missions"],
)
def create_mission_endpoint(request: MissionCreateRequest) -> Mission:
    """Create a mission using the existing service-layer business rules."""
    try:
        return create_mission(
            team_id=request.team_id,
            disaster_id=request.disaster_id,
            destination_latitude=request.destination_latitude,
            destination_longitude=request.destination_longitude,
            priority=request.priority,
            hospital_id=request.hospital_id,
            vehicle_id=request.vehicle_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/mission/{mission_id}",
    response_model=Mission,
    summary="Get a rescue mission",
    description="Retrieve a mission by its mission identifier from the in-memory mission service.",
    response_description="The requested mission record.",
    tags=["Missions"],
)
def get_mission_endpoint(mission_id: str) -> Mission:
    """Return the mission matching the supplied mission identifier."""
    try:
        return get_mission(mission_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/mission/{mission_id}/status",
    response_model=Mission,
    summary="Update a rescue mission status",
    description=(
        "Update the lifecycle status of an existing mission, while enforcing the mission "
        "service's transition rules and team availability synchronization."
    ),
    response_description="The updated mission record.",
    tags=["Missions"],
)
def update_mission_status_endpoint(mission_id: str, request: MissionStatusUpdateRequest) -> Mission:
    """Update the status of an existing mission using the service's transition rules."""
    try:
        return update_mission_status(mission_id, request.status)
    except ValueError as exc:
        message = str(exc)
        if "does not exist" in message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
