"""Operator-confirmed adapter endpoint for external disaster detections."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from backend.rescue.models.detection_integration import DisasterDetectionAdapter
from backend.rescue.models.mission import Mission, MissionPriority
from backend.rescue.services.detection_integration_service import (
    DuplicateDetectionError,
    create_mission_from_detection,
)

router = APIRouter()


class DetectionMissionCreateRequest(BaseModel):
    """Validated detection handoff and explicit operator mission confirmation."""

    model_config = ConfigDict(extra="forbid")

    detection: DisasterDetectionAdapter
    team_id: str = Field(..., min_length=1)
    priority: MissionPriority = MissionPriority.MEDIUM
    hospital_id: str | None = None
    vehicle_id: str | None = None
    confirmed: bool = Field(
        ..., description="Must be true to authorize mission creation"
    )


@router.post(
    "/mission/from-detection",
    response_model=Mission,
    status_code=status.HTTP_201_CREATED,
    summary="Create a mission from a confirmed detection",
    description=(
        "Operator adapter contract, not a disaster-detection feed. It accepts the "
        "documented DisasterDetectionAdapter fields, uses disaster ID and coordinates "
        "from the detection, and creates an ASSIGNED mission only when confirmed is true. "
        "A detection ID can be linked to only one mission."
    ),
    tags=["Detection integration"],
)
def create_mission_from_detection_endpoint(
    request: DetectionMissionCreateRequest,
) -> Mission:
    """Create a mission from validated detector data only after explicit confirmation."""
    try:
        return create_mission_from_detection(
            request.detection,
            team_id=request.team_id,
            priority=request.priority,
            confirmed=request.confirmed,
            hospital_id=request.hospital_id,
            vehicle_id=request.vehicle_id,
        )
    except DuplicateDetectionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
