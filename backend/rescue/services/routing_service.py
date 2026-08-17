"""Development/mock routing service for the Resource & Rescue Management module.

This module intentionally provides deterministic routing estimates without any
external provider integration. It is designed to be replaceable by a real routing
provider later while keeping the same service interface and behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.rescue.models.route import RouteRequest, RouteResponse
from backend.rescue.utils.geo import haversine_km


DEFAULT_AVERAGE_SPEED_KMH = 35.0
DEFAULT_RISK_BASELINE = 0.15


@dataclass(frozen=True)
class RoutingServiceConfig:
    """Development configuration for the mock routing service."""

    average_speed_kmh: float = DEFAULT_AVERAGE_SPEED_KMH
    risk_baseline: float = DEFAULT_RISK_BASELINE


class MockRoutingService:
    """Deterministic mock routing provider for development and testing."""

    def __init__(self, config: RoutingServiceConfig | None = None) -> None:
        self.config = config or RoutingServiceConfig()

    def route(self, request: RouteRequest) -> RouteResponse:
        """Calculate a simple mock route estimate between two coordinates.

        This is a placeholder implementation intended for local development and
        deterministic testing. It does not call any external provider.
        """
        distance_km = haversine_km(
            request.origin_latitude,
            request.origin_longitude,
            request.destination_latitude,
            request.destination_longitude,
        )

        duration_minutes = (distance_km / self.config.average_speed_kmh) * 60.0

        # Placeholder risk score based on distance and a small baseline.
        # This is deliberately simple and transparent for mock/testing purposes.
        risk_score = min(1.0, self.config.risk_baseline + (distance_km / 2000.0))

        status = "OK" if risk_score < 0.7 else "CAUTION"
        explanation = (
            "Development/mock routing provider: using deterministic geographic "
            "distance and average-speed approximation for planning estimates."
        )

        return RouteResponse(
            distance_km=round(distance_km, 2),
            estimated_duration_minutes=round(duration_minutes, 2),
            route_risk_score=round(risk_score, 4),
            route_status=status,
            explanation=explanation,
        )


def calculate_route(request: RouteRequest, average_speed_kmh: float = DEFAULT_AVERAGE_SPEED_KMH) -> RouteResponse:
    """Convenience function that uses the mock routing service.

    This function keeps the interface simple for tests and callers while still
    allowing a provider-backed implementation to replace the service later.
    """
    service = MockRoutingService(
        RoutingServiceConfig(average_speed_kmh=average_speed_kmh)
    )
    return service.route(request)
