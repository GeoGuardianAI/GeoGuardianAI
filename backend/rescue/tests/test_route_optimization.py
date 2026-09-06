"""Unit tests for route optimization models."""

from pydantic import ValidationError
import pytest

from backend.rescue.models.route_optimization import (
    RouteCandidate,
    RouteOptimizationRequest,
    RouteOptimizationResult,
)


def _request_kwargs() -> dict:
    return {
        "origin_latitude": 40.0,
        "origin_longitude": -70.0,
        "destination_latitude": 41.0,
        "destination_longitude": -71.0,
    }


def _candidate_kwargs() -> dict:
    return {
        "route_id": "route-a",
        "distance_km": 10.0,
        "estimated_duration_minutes": 20.0,
        "route_risk_score": 0.2,
    }


def test_valid_optimization_request_and_candidate_can_be_created() -> None:
    request = RouteOptimizationRequest(**_request_kwargs())
    candidate = RouteCandidate(**_candidate_kwargs())
    result = RouteOptimizationResult(
        selected_route=candidate,
        candidates=[candidate],
        optimization_score=80.0,
        reasoning="The only route was selected.",
    )
    assert request.risk_tolerance == 0.5
    assert result.selected_route.route_id == "route-a"


@pytest.mark.parametrize(
    "field, values",
    [
        ("origin_latitude", [90.1, -90.1]),
        ("origin_longitude", [180.1, -180.1]),
        ("destination_latitude", [90.1, -90.1]),
        ("destination_longitude", [180.1, -180.1]),
    ],
)
def test_invalid_coordinates_are_rejected(field: str, values: list[float]) -> None:
    for value in values:
        data = _request_kwargs()
        data[field] = value
        with pytest.raises(ValidationError):
            RouteOptimizationRequest(**data)


@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_invalid_risk_tolerance_is_rejected(value: float) -> None:
    data = _request_kwargs()
    data["risk_tolerance"] = value
    with pytest.raises(ValidationError):
        RouteOptimizationRequest(**data)


@pytest.mark.parametrize("field", ["disaster_id"])
def test_blank_optional_disaster_id_is_rejected(field: str) -> None:
    data = _request_kwargs()
    data[field] = "   "
    with pytest.raises(ValidationError):
        RouteOptimizationRequest(**data)


@pytest.mark.parametrize(
    "field, value",
    [
        ("route_id", ""),
        ("distance_km", -1.0),
        ("estimated_duration_minutes", -1.0),
        ("route_risk_score", -0.1),
        ("route_risk_score", 1.1),
    ],
)
def test_invalid_candidate_values_are_rejected(field: str, value: object) -> None:
    data = _candidate_kwargs()
    data[field] = value
    with pytest.raises(ValidationError):
        RouteCandidate(**data)


def test_result_requires_at_least_one_candidate() -> None:
    candidate = RouteCandidate(**_candidate_kwargs())
    with pytest.raises(ValidationError):
        RouteOptimizationResult(
            selected_route=candidate,
            candidates=[],
            optimization_score=80.0,
            reasoning="No candidates.",
        )