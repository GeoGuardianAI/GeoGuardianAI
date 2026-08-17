"""Unit tests for the `AllocationRequest` and `AllocationRecommendation` Pydantic models."""

from pydantic import ValidationError
import pytest

from backend.rescue.models.allocation import AllocationRecommendation, AllocationRequest
from backend.rescue.models.hospital import Hospital
from backend.rescue.models.rescue_team import Availability, RescueTeam, TeamType


def _base_request_kwargs() -> dict:
    return {
        "disaster_id": "disaster-001",
        "disaster_type": "flood",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "severity": 3,
        "required_specialization": "search",
    }


def _base_hospital() -> Hospital:
    return Hospital(
        hospital_id="h-001",
        name="Example Hospital",
        latitude=40.7128,
        longitude=-74.0060,
        bed_capacity=100,
        available_beds=20,
        icu_capacity=10,
        available_icu=2,
        emergency_available=True,
    )


def _base_rescue_team() -> RescueTeam:
    return RescueTeam(
        team_id="rt-001",
        name="Example Rescue Team",
        team_type=TeamType.SEARCH_AND_RESCUE,
        latitude=40.7128,
        longitude=-74.0060,
        members=12,
        specialization=["search", "climbing"],
        availability=Availability.AVAILABLE,
        current_mission_id=None,
    )


def test_valid_allocation_request_can_be_created() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    assert request.disaster_id == "disaster-001"
    assert request.disaster_type == "flood"
    assert request.required_specialization == "search"


@pytest.mark.parametrize("lat", [90.1, -90.1, 100.0])
def test_invalid_latitude_is_rejected(lat: float) -> None:
    data = _base_request_kwargs()
    data["latitude"] = lat
    with pytest.raises(ValidationError):
        AllocationRequest(**data)


@pytest.mark.parametrize("lon", [180.1, -180.1, 200.0])
def test_invalid_longitude_is_rejected(lon: float) -> None:
    data = _base_request_kwargs()
    data["longitude"] = lon
    with pytest.raises(ValidationError):
        AllocationRequest(**data)


@pytest.mark.parametrize("severity", [0, -1])
def test_severity_below_1_is_rejected(severity: int) -> None:
    data = _base_request_kwargs()
    data["severity"] = severity
    with pytest.raises(ValidationError):
        AllocationRequest(**data)


@pytest.mark.parametrize("severity", [6, 10])
def test_severity_above_5_is_rejected(severity: int) -> None:
    data = _base_request_kwargs()
    data["severity"] = severity
    with pytest.raises(ValidationError):
        AllocationRequest(**data)


@pytest.mark.parametrize("disaster_id", ["", "   "])
def test_empty_disaster_id_is_rejected(disaster_id: str) -> None:
    data = _base_request_kwargs()
    data["disaster_id"] = disaster_id
    with pytest.raises(ValidationError):
        AllocationRequest(**data)


@pytest.mark.parametrize("disaster_type", ["", "   "])
def test_empty_disaster_type_is_rejected(disaster_type: str) -> None:
    data = _base_request_kwargs()
    data["disaster_type"] = disaster_type
    with pytest.raises(ValidationError):
        AllocationRequest(**data)


def test_required_specialization_can_be_none() -> None:
    data = _base_request_kwargs()
    data["required_specialization"] = None
    request = AllocationRequest(**data)
    assert request.required_specialization is None


def test_required_specialization_can_contain_a_value() -> None:
    data = _base_request_kwargs()
    data["required_specialization"] = "medical"
    request = AllocationRequest(**data)
    assert request.required_specialization == "medical"


def test_valid_allocation_recommendation_can_be_created() -> None:
    recommendation = AllocationRecommendation(
        disaster_id="disaster-001",
        recommended_hospital=_base_hospital(),
        recommended_rescue_team=_base_rescue_team(),
        priority_score=84.5,
        estimated_distance_km=12.5,
        reasoning="Nearest compatible rescue team and hospital were selected.",
    )

    assert recommendation.disaster_id == "disaster-001"
    assert recommendation.priority_score == 84.5
    assert recommendation.estimated_distance_km == 12.5


@pytest.mark.parametrize("priority_score", [-0.1, -1.0])
def test_priority_score_below_0_is_rejected(priority_score: float) -> None:
    with pytest.raises(ValidationError):
        AllocationRecommendation(
            disaster_id="disaster-001",
            recommended_hospital=_base_hospital(),
            recommended_rescue_team=_base_rescue_team(),
            priority_score=priority_score,
            estimated_distance_km=12.5,
            reasoning="Valid reasoning.",
        )


@pytest.mark.parametrize("priority_score", [100.1, 200.0])
def test_priority_score_above_100_is_rejected(priority_score: float) -> None:
    with pytest.raises(ValidationError):
        AllocationRecommendation(
            disaster_id="disaster-001",
            recommended_hospital=_base_hospital(),
            recommended_rescue_team=_base_rescue_team(),
            priority_score=priority_score,
            estimated_distance_km=12.5,
            reasoning="Valid reasoning.",
        )


def test_negative_estimated_distance_km_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AllocationRecommendation(
            disaster_id="disaster-001",
            recommended_hospital=_base_hospital(),
            recommended_rescue_team=_base_rescue_team(),
            priority_score=70.0,
            estimated_distance_km=-1.0,
            reasoning="Valid reasoning.",
        )


@pytest.mark.parametrize("reasoning", ["", "   "])
def test_empty_reasoning_is_rejected(reasoning: str) -> None:
    with pytest.raises(ValidationError):
        AllocationRecommendation(
            disaster_id="disaster-001",
            recommended_hospital=_base_hospital(),
            recommended_rescue_team=_base_rescue_team(),
            priority_score=70.0,
            estimated_distance_km=12.5,
            reasoning=reasoning,
        )
