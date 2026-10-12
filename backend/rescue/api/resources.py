from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.rescue.models.allocation import (
    AllocationRecommendation,
    AllocationRequest,
    MissionResourceReadinessRequest,
    MissionResourceReadinessResponse,
    MissionResourceRecommendation,
    MissionResourceRecommendationRequest,
)
from backend.rescue.services.allocation_service import (
    NoSuitableEmergencyResourceError,
    NoSuitableHospitalError,
    NoSuitableRescueTeamError,
    assess_mission_resource_readiness,
    recommend_resources,
    recommend_resources_for_mission,
)

router = APIRouter()


@router.post(
    "/allocate-resource",
    response_model=AllocationRecommendation,
    summary="Allocate disaster response resources",
    description=(
        "Evaluate a disaster allocation request and return the recommended hospital and "
        "rescue team according to the allocation service layer."
    ),
    response_description="Recommended hospital and rescue team for the disaster response",
    tags=["Resource Allocation"],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "No suitable hospital or rescue team exists for the request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "error": "No suitable rescue team exists for the requested disaster.",
                            "message": "No suitable rescue team exists for the requested disaster coordinates and specialization.",
                        }
                    }
                }
            },
        }
    },
)
def allocate_resource(request: AllocationRequest) -> AllocationRecommendation:
    """Return a resource recommendation for the given disaster request."""
    try:
        return recommend_resources(request)
    except NoSuitableRescueTeamError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "No suitable rescue team exists for the requested disaster.",
                "message": str(exc),
            },
        ) from exc
    except NoSuitableHospitalError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "No suitable hospital exists for the requested coordinates.",
                "message": str(exc),
            },
        ) from exc
    except NoSuitableEmergencyResourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "No suitable emergency resource exists for the request.",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/recommend-resources-for-mission",
    response_model=MissionResourceRecommendation,
    summary="Recommend emergency resources for a mission",
    description=(
        "Return read-only recommendations near an existing, non-terminal mission's "
        "destination. An optional resource type is a strict filter and quantity is a "
        "minimum available amount. Eligible resources rank by available quantity "
        "descending, distance ascending, resource type ascending, then resource ID "
        "ascending. No inventory is reserved or allocated."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "The mission is terminal or the request cannot be satisfied."
        },
        status.HTTP_404_NOT_FOUND: {"description": "The mission does not exist."},
    },
    tags=["Resource Allocation"],
)
def recommend_resources_for_mission_endpoint(
    request: MissionResourceRecommendationRequest,
) -> MissionResourceRecommendation:
    """Return eligible resource recommendations without changing inventory."""
    try:
        return recommend_resources_for_mission(request)
    except NoSuitableEmergencyResourceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        if "does not exist" in message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


@router.post(
    "/assess-resource-readiness-for-mission",
    response_model=MissionResourceReadinessResponse,
    summary="Assess resource readiness for a mission",
    description=(
        "Assess caller-supplied resource type and quantity requirements for an existing "
        "non-terminal mission. Inventory availability and active allocations to that "
        "mission are reported separately; they are disjoint quantities and both count "
        "toward requirement coverage. The assessment does not allocate resources."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "The mission is terminal or the assessment cannot be completed."
        },
        status.HTTP_404_NOT_FOUND: {"description": "The mission does not exist."},
    },
    tags=["Resource Allocation"],
)
def assess_resource_readiness_for_mission_endpoint(
    request: MissionResourceReadinessRequest,
) -> MissionResourceReadinessResponse:
    """Assess explicitly requested mission resources without mutating state."""
    try:
        return assess_mission_resource_readiness(request)
    except ValueError as exc:
        message = str(exc)
        if "does not exist" in message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
