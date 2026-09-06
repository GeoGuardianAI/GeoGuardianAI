"""Deterministic route candidate optimization service."""

from __future__ import annotations

from backend.rescue.models.route_optimization import (
    RouteCandidate,
    RouteOptimizationRequest,
    RouteOptimizationResult,
)

DISTANCE_WEIGHT = 0.40
DURATION_WEIGHT = 0.30
RISK_WEIGHT = 0.30
RISK_PENALTY_FACTOR = 0.80


def optimize_route(
    request: RouteOptimizationRequest,
    candidates: list[RouteCandidate],
) -> RouteOptimizationResult:
    """Select the highest-scoring route from deterministic candidate options.

    Distance, duration, and route risk contribute 40%, 30%, and 30%. Distance
    and duration are normalized relative to the supplied candidate set. Routes
    exceeding the request risk tolerance receive a 20% score penalty but remain
    eligible for selection.
    """
    if not candidates:
        raise ValueError("at least one route candidate is required")

    max_distance = max(candidate.distance_km for candidate in candidates)
    max_duration = max(
        candidate.estimated_duration_minutes for candidate in candidates
    )

    scored_candidates = [
        (
            candidate,
            _final_score(
                candidate,
                request.risk_tolerance,
                max_distance,
                max_duration,
            ),
        )
        for candidate in candidates
    ]
    selected_route, selected_score = sorted(
        scored_candidates,
        key=lambda item: (
            -item[1],
            item[0].route_risk_score,
            item[0].estimated_duration_minutes,
            item[0].distance_km,
            item[0].route_id,
        ),
    )[0]

    optimization_score = round(max(0.0, min(100.0, selected_score * 100)), 2)
    reasoning = (
        f"Selected route '{selected_route.route_id}' with distance "
        f"{selected_route.distance_km:.2f} km, estimated duration "
        f"{selected_route.estimated_duration_minutes:.2f} minutes, and risk "
        f"{selected_route.route_risk_score:.2f}. Risk tolerance was "
        f"{request.risk_tolerance:.2f}; routes above tolerance receive a 20% "
        f"penalty. Final optimization score is {optimization_score:.2f}/100."
    )

    return RouteOptimizationResult(
        selected_route=selected_route,
        candidates=candidates,
        optimization_score=optimization_score,
        reasoning=reasoning,
    )


def _final_score(
    candidate: RouteCandidate,
    risk_tolerance: float,
    max_distance: float,
    max_duration: float,
) -> float:
    """Return one candidate's normalized and tolerance-adjusted score."""
    distance_score = (
        1.0 if max_distance == 0.0 else 1.0 - candidate.distance_km / max_distance
    )
    duration_score = (
        1.0
        if max_duration == 0.0
        else 1.0 - candidate.estimated_duration_minutes / max_duration
    )
    risk_score = 1.0 - candidate.route_risk_score
    overall_score = (
        distance_score * DISTANCE_WEIGHT
        + duration_score * DURATION_WEIGHT
        + risk_score * RISK_WEIGHT
    )
    if candidate.route_risk_score > risk_tolerance:
        return overall_score * RISK_PENALTY_FACTOR
    return overall_score