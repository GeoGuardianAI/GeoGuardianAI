from __future__ import annotations

from fastapi import APIRouter

from backend.rescue.models.route import RouteRequest, RouteResponse
from backend.rescue.services.routing_service import calculate_route

router = APIRouter()


@router.post(
    "/calculate-route",
    response_model=RouteResponse,
    summary="Calculate emergency response route",
    description=(
        "Provide a deterministic mock route estimate between two geographic points "
        "for emergency response planning and risk evaluation."
    ),
    response_description=(
        "Returns the estimated distance in kilometers, travel duration in minutes, "
        "route risk score, route status, and a human-readable explanation."
    ),
    tags=["Routing"],
)
def calculate_route_endpoint(request: RouteRequest) -> RouteResponse:
    """Return a deterministic route estimate for the provided geographic request."""
    return calculate_route(request)
