from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.rescue.models.mission import Mission, MissionPriority
from backend.rescue.services.mission_service import create_mission

router = APIRouter()


class TeamDeploymentRequest(BaseModel):
    """Request payload for deploying a rescue team to a disaster."""

    team_id: str = Field(..., description="Rescue team identifier to deploy")
    disaster_id: str = Field(..., description="Disaster event associated with the deployment")
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
        description="Operational priority for the deployment",
    )
    hospital_id: str | None = Field(
        default=None,
        description="Associated hospital identifier, if applicable",
    )
    vehicle_id: str | None = Field(
        default=None,
        description="Associated vehicle identifier, if applicable",
    )


@router.post(
    "/deploy-team",
    response_model=Mission,
    status_code=status.HTTP_201_CREATED,
    summary="Deploy a rescue team",
    description=(
        "Create an assigned mission for an available rescue team using the existing "
        "mission management service."
    ),
    response_description="The created deployment mission.",
    tags=["Deployment"],
)
def deploy_team(request: TeamDeploymentRequest) -> Mission:
    """Deploy a team by delegating mission creation to the mission service."""
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