"""Unit tests for the deterministic route optimization service."""

import pytest

from backend.rescue.models.route_optimization import (
    RouteCandidate,
    RouteOptimizationRequest,
)
from backend.rescue.services.route_optimization_service import optimize_route


def _request(**overrides: object) -> RouteOptimizationRequest:
    values: dict[str, object] = {
        "origin_latitude": 40.0,
        "origin_longitude": -70.0,
        "destination_latitude": 41.0,
        "destination_longitude": -71.0,
        "risk_tolerance": 0.5,
    }
    values.update(overrides)
    return RouteOptimizationRequest(**values)


def _candidate(
    route_id: str,
    distance_km: float,
    duration: float,
    risk: float,
) -> RouteCandidate:
    return RouteCandidate(
        route_id=route_id,
        distance_km=distance_km,
        estimated_duration_minutes=duration,
        route_risk_score=risk,
    )


def test_best_route_is_selected() -> None:
    candidates = [
        _candidate("long", 100.0, 100.0, 0.3),
        _candidate("best", 20.0, 20.0, 0.1),
        _candidate("risky", 10.0, 10.0, 0.9),
    ]
    result = optimize_route(_request(), candidates)
    assert result.selected_route.route_id == "best"


def test_distance_duration_and_risk_weights_affect_score() -> None:
    candidates = [
        _candidate("balanced", 0.0, 0.0, 0.5),
        _candidate("risky", 0.0, 0.0, 0.0),
        _candidate("slow", 100.0, 100.0, 0.0),
    ]
    result = optimize_route(_request(), candidates)
    assert result.selected_route.route_id == "risky"


def test_risk_tolerance_penalizes_but_does_not_exclude_route() -> None:
    candidates = [
        _candidate("over-tolerance", 10.0, 10.0, 0.4),
        _candidate("within-tolerance", 10.0, 10.0, 0.3),
    ]
    result = optimize_route(_request(risk_tolerance=0.3), candidates)
    assert result.selected_route.route_id == "within-tolerance"
    assert "20%" in result.reasoning


def test_zero_distance_uses_one_for_every_distance_factor() -> None:
    candidates = [
        _candidate("low-risk", 0.0, 10.0, 0.1),
        _candidate("high-risk", 0.0, 10.0, 0.9),
    ]
    result = optimize_route(_request(), candidates)
    assert result.selected_route.route_id == "low-risk"


def test_zero_duration_uses_one_for_every_duration_factor() -> None:
    candidates = [
        _candidate("low-risk", 10.0, 0.0, 0.1),
        _candidate("high-risk", 10.0, 0.0, 0.9),
    ]
    result = optimize_route(_request(), candidates)
    assert result.selected_route.route_id == "low-risk"


def test_ties_break_by_risk_then_duration_then_distance_then_route_id() -> None:
    candidates = [
        _candidate("z-route", 10.0, 10.0, 0.2),
        _candidate("a-route", 10.0, 10.0, 0.2),
        _candidate("low-risk", 10.0, 10.0, 0.1),
    ]
    result = optimize_route(_request(), candidates)
    assert result.selected_route.route_id == "low-risk"

    tied_candidates = [
        _candidate("z-route", 10.0, 10.0, 0.2),
        _candidate("a-route", 10.0, 10.0, 0.2),
    ]
    tied_result = optimize_route(_request(), tied_candidates)
    assert tied_result.selected_route.route_id == "a-route"


def test_optimization_score_stays_within_bounds() -> None:
    result = optimize_route(
        _request(), [_candidate("route", 0.0, 0.0, 0.0)]
    )
    assert 0.0 <= result.optimization_score <= 100.0


def test_empty_candidates_raise_value_error() -> None:
    with pytest.raises(ValueError, match="at least one route candidate"):
        optimize_route(_request(), [])


def test_reasoning_explains_selection_factors() -> None:
    result = optimize_route(
        _request(risk_tolerance=0.4), [_candidate("route-a", 12.5, 18.0, 0.6)]
    )
    assert "route-a" in result.reasoning
    assert "12.50 km" in result.reasoning
    assert "18.00 minutes" in result.reasoning
    assert "0.60" in result.reasoning
    assert "0.40" in result.reasoning


def test_repeated_optimization_is_deterministic() -> None:
    candidates = [
        _candidate("route-a", 10.0, 20.0, 0.2),
        _candidate("route-b", 20.0, 10.0, 0.3),
    ]
    first = optimize_route(_request(), candidates)
    second = optimize_route(_request(), candidates)
    assert first == second