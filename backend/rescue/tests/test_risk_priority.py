"""Unit tests for the risk-priority Pydantic models."""

from pydantic import ValidationError
import pytest

from backend.rescue.models.risk_priority import (
    PriorityLevel,
    RiskPriorityRequest,
    RiskPriorityResult,
)


def _base_kwargs() -> dict:
    return {
        "disaster_id": "disaster-101",
        "disaster_type": "flood",
        "latitude": 40.0,
        "longitude": -70.0,
        "severity": 3,
        "affected_population": 1000,
    }


def test_valid_risk_priority_request_can_be_created() -> None:
    request = RiskPriorityRequest(**_base_kwargs())
    assert request.disaster_id == "disaster-101"
    assert request.critical_infrastructure is False


def test_valid_risk_priority_result_can_be_created() -> None:
    result = RiskPriorityResult(
        disaster_id="disaster-101",
        risk_score=50.0,
        priority_level=PriorityLevel.HIGH,
        reasoning="Risk factors produce a high priority.",
    )
    assert result.priority_level == PriorityLevel.HIGH


@pytest.mark.parametrize("severity", [0, 6])
def test_invalid_severity_is_rejected(severity: int) -> None:
    data = _base_kwargs()
    data["severity"] = severity
    with pytest.raises(ValidationError):
        RiskPriorityRequest(**data)


@pytest.mark.parametrize("latitude", [-90.1, 90.1])
def test_invalid_latitude_is_rejected(latitude: float) -> None:
    data = _base_kwargs()
    data["latitude"] = latitude
    with pytest.raises(ValidationError):
        RiskPriorityRequest(**data)


@pytest.mark.parametrize("longitude", [-180.1, 180.1])
def test_invalid_longitude_is_rejected(longitude: float) -> None:
    data = _base_kwargs()
    data["longitude"] = longitude
    with pytest.raises(ValidationError):
        RiskPriorityRequest(**data)


def test_invalid_population_is_rejected() -> None:
    data = _base_kwargs()
    data["affected_population"] = -1
    with pytest.raises(ValidationError):
        RiskPriorityRequest(**data)


@pytest.mark.parametrize("field", ["disaster_id", "disaster_type"])
@pytest.mark.parametrize("value", ["", "   "])
def test_empty_disaster_text_is_rejected(field: str, value: str) -> None:
    data = _base_kwargs()
    data[field] = value
    with pytest.raises(ValidationError):
        RiskPriorityRequest(**data)