from __future__ import annotations

from fastapi import APIRouter

from backend.rescue.models.risk_priority import RiskPriorityRequest, RiskPriorityResult
from backend.rescue.services.risk_priority_service import calculate_risk_priority

router = APIRouter()


@router.post(
    "/risk-priority",
    response_model=RiskPriorityResult,
    summary="Calculate disaster risk priority",
    description=(
        "Calculate a deterministic risk score and priority level for a disaster "
        "using severity, affected population, and critical infrastructure."
    ),
    response_description="Calculated disaster risk score, priority level, and reasoning.",
    tags=["Risk Priority"],
)
def calculate_risk_priority_endpoint(
    request: RiskPriorityRequest,
) -> RiskPriorityResult:
    """Calculate risk priority using the existing scoring service."""
    return calculate_risk_priority(request)