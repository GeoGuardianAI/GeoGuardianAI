"""Unit tests for the `RescueTeam` Pydantic model.

Uses pytest and Pydantic v2 validation behaviour.
"""

from pydantic import ValidationError
import pytest

from backend.rescue.models.rescue_team import Availability, RescueTeam, TeamType


def _base_kwargs() -> dict:
    return {
        "team_id": "rt-101",
        "name": "Alpha Search Team",
        "team_type": TeamType.SEARCH_AND_RESCUE,
        "latitude": 45.0,
        "longitude": -75.0,
        "members": 8,
        "specialization": ["mountain rescue", "medical support"],
        "availability": Availability.AVAILABLE,
        "current_mission_id": None,
    }


def test_valid_rescue_team_can_be_created() -> None:
    team = RescueTeam(**_base_kwargs())
    assert team.team_id == "rt-101"
    assert team.name == "Alpha Search Team"
    assert team.team_type == TeamType.SEARCH_AND_RESCUE


@pytest.mark.parametrize("lat", [90.1, -90.1, 100.0])
def test_invalid_latitude_is_rejected(lat: float) -> None:
    data = _base_kwargs()
    data["latitude"] = lat
    with pytest.raises(ValidationError):
        RescueTeam(**data)


@pytest.mark.parametrize("lon", [180.1, -180.1, 200.0])
def test_invalid_longitude_is_rejected(lon: float) -> None:
    data = _base_kwargs()
    data["longitude"] = lon
    with pytest.raises(ValidationError):
        RescueTeam(**data)


def test_negative_member_count_is_rejected() -> None:
    data = _base_kwargs()
    data["members"] = -1
    with pytest.raises(ValidationError):
        RescueTeam(**data)


@pytest.mark.parametrize(
    "team_type",
    [
        TeamType.SEARCH_AND_RESCUE,
        TeamType.MEDICAL,
        TeamType.FIRE_AND_RESCUE,
        TeamType.WATER_RESCUE,
        TeamType.DISASTER_RESPONSE,
    ],
)
def test_each_valid_teamtype_works(team_type: TeamType) -> None:
    data = _base_kwargs()
    data["team_type"] = team_type
    team = RescueTeam(**data)
    assert team.team_type == team_type


@pytest.mark.parametrize(
    "availability",
    [
        Availability.AVAILABLE,
        Availability.ASSIGNED,
        Availability.DEPLOYED,
        Availability.UNAVAILABLE,
    ],
)
def test_each_valid_availability_value_works(availability: Availability) -> None:
    data = _base_kwargs()
    data["availability"] = availability
    team = RescueTeam(**data)
    assert team.availability == availability


def test_current_mission_id_can_be_none() -> None:
    data = _base_kwargs()
    team = RescueTeam(**data)
    assert team.current_mission_id is None


def test_current_mission_id_can_contain_a_mission_id() -> None:
    data = _base_kwargs()
    data["current_mission_id"] = "mission-42"
    team = RescueTeam(**data)
    assert team.current_mission_id == "mission-42"


def test_specialization_accepts_multiple_specializations() -> None:
    data = _base_kwargs()
    data["specialization"] = ["water rescue", "evacuation", "triage"]
    team = RescueTeam(**data)
    assert team.specialization == ["water rescue", "evacuation", "triage"]


@pytest.mark.parametrize(
    "invalid_team_type",
    ["INVALID", "search_and_rescue", "medical_team", ""],
)
def test_invalid_enum_values_are_rejected(invalid_team_type: str) -> None:
    data = _base_kwargs()
    data["team_type"] = invalid_team_type
    with pytest.raises(ValidationError):
        RescueTeam(**data)


@pytest.mark.parametrize(
    "invalid_availability",
    ["INVALID", "assigned_now", "deployed_state", ""],
)
def test_invalid_availability_enum_values_are_rejected(invalid_availability: str) -> None:
    data = _base_kwargs()
    data["availability"] = invalid_availability
    with pytest.raises(ValidationError):
        RescueTeam(**data)
