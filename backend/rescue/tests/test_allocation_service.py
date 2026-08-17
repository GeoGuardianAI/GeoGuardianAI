"""Unit tests for the deterministic allocation service."""

from pydantic import ValidationError
import pytest

from backend.rescue.models.allocation import AllocationRequest
from backend.rescue.models.hospital import Hospital
from backend.rescue.models.rescue_team import RescueTeam
from backend.rescue.services.allocation_service import (
    NoSuitableRescueTeamError,
    recommend_resources,
)


def _base_request_kwargs() -> dict:
    return {
        "disaster_id": "disaster-001",
        "disaster_type": "flood",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "severity": 3,
        "required_specialization": None,
    }


def test_valid_disaster_produces_an_allocation_recommendation() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert recommendation is not None
    assert recommendation.disaster_id == "disaster-001"


def test_recommended_hospital_is_a_hospital_instance() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert isinstance(recommendation.recommended_hospital, Hospital)


def test_recommended_rescue_team_is_a_rescueteam_instance() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert isinstance(recommendation.recommended_rescue_team, RescueTeam)


def test_recommendation_contains_correct_disaster_id() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert recommendation.disaster_id == request.disaster_id


def test_priority_score_is_between_0_and_100() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert 0 <= recommendation.priority_score <= 100


def test_estimated_distance_is_non_negative() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert recommendation.estimated_distance_km >= 0


def test_reasoning_is_non_empty() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert recommendation.reasoning.strip() != ""


def test_required_specialization_causes_service_to_select_matching_team() -> None:
    request = AllocationRequest(**{**_base_request_kwargs(), "required_specialization": "search"})
    recommendation = recommend_resources(request)

    assert "search" in [item.lower() for item in recommendation.recommended_rescue_team.specialization]


def test_unavailable_team_is_never_selected() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert recommendation.recommended_rescue_team.availability.value == "AVAILABLE"


def test_when_no_suitable_specialization_exists_a_clear_domain_exception_is_raised() -> None:
    request = AllocationRequest(**{**_base_request_kwargs(), "required_specialization": "nonexistent-skill"})

    with pytest.raises(NoSuitableRescueTeamError, match="No suitable rescue team exists"):
        recommend_resources(request)


@pytest.mark.parametrize("latitude", [-90.1, 90.1])
def test_invalid_latitude_is_rejected(latitude: float) -> None:
    data = _base_request_kwargs()
    data["latitude"] = latitude

    with pytest.raises(ValidationError):
        AllocationRequest(**data)


@pytest.mark.parametrize("longitude", [-180.1, 180.1])
def test_invalid_longitude_is_rejected(longitude: float) -> None:
    data = _base_request_kwargs()
    data["longitude"] = longitude

    with pytest.raises(ValidationError):
        AllocationRequest(**data)


def test_same_input_produces_the_same_recommendation() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    first = recommend_resources(request)
    second = recommend_resources(request)

    assert first == second
