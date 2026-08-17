from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.rescue.models.allocation import AllocationRecommendation, AllocationRequest
from backend.rescue.services.allocation_service import (
    NoSuitableHospitalError,
    NoSuitableRescueTeamError,
    recommend_resources,
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
