"""Unit tests for the risk-priority scoring service."""

import pytest

from backend.rescue.models.risk_priority import PriorityLevel, RiskPriorityRequest
from backend.rescue.services.risk_priority_service import calculate_risk_priority


def _request(**overrides: object) -> RiskPriorityRequest:
    values: dict[str, object] = {
        "disaster_id": "disaster-101",
        "disaster_type": "flood",
        "latitude": 40.0,
        "longitude": -70.0,
        "severity": 1,
        "affected_population": 0,
        "critical_infrastructure": False,
    }
    values.update(overrides)
    return RiskPriorityRequest(**values)


def test_minimum_risk_is_low() -> None:
    result = calculate_risk_priority(_request())
    assert result.risk_score == 0.0
    assert result.priority_level == PriorityLevel.LOW


def test_medium_risk_is_medium() -> None:
    result = calculate_risk_priority(_request(severity=3, affected_population=3333))
    assert 25.0 <= result.risk_score < 50.0
    assert result.priority_level == PriorityLevel.MEDIUM


def test_high_risk_is_high() -> None:
    result = calculate_risk_priority(_request(severity=4, affected_population=5000))
    assert 50.0 <= result.risk_score < 75.0
    assert result.priority_level == PriorityLevel.HIGH


def test_critical_risk_is_critical() -> None:
    result = calculate_risk_priority(
        _request(severity=5, affected_population=10000, critical_infrastructure=True)
    )
    assert result.risk_score == 100.0
    assert result.priority_level == PriorityLevel.CRITICAL


def test_population_is_normalized_at_cap() -> None:
    at_cap = calculate_risk_priority(_request(affected_population=10000))
    above_cap = calculate_risk_priority(_request(affected_population=15000))
    assert at_cap.risk_score == above_cap.risk_score


def test_critical_infrastructure_increases_score() -> None:
    without_infrastructure = calculate_risk_priority(_request(severity=3, affected_population=5000))
    with_infrastructure = calculate_risk_priority(
        _request(severity=3, affected_population=5000, critical_infrastructure=True)
    )
    assert with_infrastructure.risk_score == without_infrastructure.risk_score + 20.0


def test_score_stays_within_bounds() -> None:
    for request in (
        _request(severity=1, affected_population=0),
        _request(severity=5, affected_population=100000, critical_infrastructure=True),
    ):
        result = calculate_risk_priority(request)
        assert 0.0 <= result.risk_score <= 100.0


def test_reasoning_explains_all_scoring_factors() -> None:
    result = calculate_risk_priority(
        _request(severity=4, affected_population=5000, critical_infrastructure=True)
    )
    assert "Severity" in result.reasoning
    assert "affected population" in result.reasoning
    assert "critical infrastructure" in result.reasoning
    assert "Final risk score" in result.reasoning
    assert "HIGH" in result.reasoning


def test_calculation_is_deterministic() -> None:
    request = _request(severity=4, affected_population=5000, critical_infrastructure=True)
    first = calculate_risk_priority(request)
    second = calculate_risk_priority(request)
    assert first == second