"""Unit tests for the rescue team service.

These tests validate deterministic, in-memory filtering and ordering behaviour
without using external services or databases.
"""

import pytest

from backend.rescue.models.rescue_team import RescueTeam
from backend.rescue.services import rescue_team_service


def test_available_teams_are_returned() -> None:
    teams = rescue_team_service.get_available_teams(40.7128, -74.0060)

    assert teams
    assert all(team.availability.value == "AVAILABLE" for team in teams)


def test_unavailable_teams_are_excluded() -> None:
    teams = rescue_team_service.get_available_teams(40.7128, -74.0060)

    excluded_ids = {"rescue-hou-01", "rescue-sea-01", "rescue-den-01"}
    assert all(team.team_id not in excluded_ids for team in teams)


def test_teams_are_ordered_by_geographic_distance() -> None:
    teams = rescue_team_service.get_available_teams(40.7128, -74.0060)

    first = teams[0]
    second = teams[1]

    assert first.team_id == "rescue-ny-01"
    assert second.team_id in {"rescue-chi-01", "rescue-miami-01", "rescue-la-01"}


def test_specialization_filtering_works() -> None:
    teams = rescue_team_service.get_available_teams(40.7128, -74.0060, specialization="search")

    assert teams
    assert all("search" in [item.lower() for item in team.specialization] for team in teams)


def test_no_matching_specialization_returns_empty_list() -> None:
    teams = rescue_team_service.get_available_teams(40.7128, -74.0060, specialization="nonexistent")
    assert teams == []


@pytest.mark.parametrize("latitude", [-90.1, 90.1])
def test_invalid_latitude_raises_value_error(latitude: float) -> None:
    with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
        rescue_team_service.get_available_teams(latitude, -74.0060)


@pytest.mark.parametrize("longitude", [-180.1, 180.1])
def test_invalid_longitude_raises_value_error(longitude: float) -> None:
    with pytest.raises(ValueError, match="longitude must be between -180 and 180"):
        rescue_team_service.get_available_teams(40.7128, longitude)


def test_location_near_known_mock_team_returns_that_team_first() -> None:
    teams = rescue_team_service.get_available_teams(40.7128, -74.0060)
    assert teams[0].team_id == "rescue-ny-01"

    near_nyc = rescue_team_service.get_available_teams(40.7128, -74.0060, specialization="mountain rescue")
    assert near_nyc[0].team_id == "rescue-ny-01"


def test_returned_objects_are_rescueteam_instances() -> None:
    teams = rescue_team_service.get_available_teams(40.7128, -74.0060)

    assert isinstance(teams, list)
    assert all(isinstance(team, RescueTeam) for team in teams)
