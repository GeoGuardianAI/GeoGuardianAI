"""API tests for rescue-team deployment."""

import pytest
from fastapi.testclient import TestClient

import backend.rescue.services.mission_service as mission_service
import backend.rescue.services.rescue_team_service as rescue_team_service
from backend.rescue.main import app

client = TestClient(app)

_ORIGINAL_TEAM_STATE = {
    team.team_id: {
        "availability": team.availability,
        "current_mission_id": team.current_mission_id,
    }
    for team in rescue_team_service._RESCUE_TEAMS
}
_ORIGINAL_MISSIONS = {
    mission_id: mission.model_copy(deep=True)
    for mission_id, mission in mission_service._MISSIONS.items()
}
_ORIGINAL_NEXT_MISSION_NUMBER = mission_service._NEXT_MISSION_NUMBER


def _restore_state() -> None:
    mission_service._MISSIONS.clear()
    mission_service._MISSIONS.update(
        {
            mission_id: mission.model_copy(deep=True)
            for mission_id, mission in _ORIGINAL_MISSIONS.items()
        }
    )
    mission_service._NEXT_MISSION_NUMBER = _ORIGINAL_NEXT_MISSION_NUMBER

    for team in rescue_team_service._RESCUE_TEAMS:
        original = _ORIGINAL_TEAM_STATE[team.team_id]
        team.availability = original["availability"]
        team.current_mission_id = original["current_mission_id"]


@pytest.fixture(autouse=True)
def reset_service_state() -> None:
    """Restore shared mission and team state around every deployment test."""
    _restore_state()
    yield
    _restore_state()


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "team_id": "rescue-ny-01",
        "disaster_id": "disaster-deployment-001",
        "destination_latitude": 40.7128,
        "destination_longitude": -74.0060,
    }
    payload.update(overrides)
    return payload


def test_successful_deployment_returns_created_mission() -> None:
    response = client.post("/deploy-team", json=_valid_payload())

    assert response.status_code == 201
    assert response.json()["team_id"] == "rescue-ny-01"
    assert response.json()["disaster_id"] == "disaster-deployment-001"
    assert response.json()["status"] == "ASSIGNED"


def test_nonexistent_team_returns_http_400() -> None:
    response = client.post("/deploy-team", json=_valid_payload(team_id="missing-team"))

    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_unavailable_team_returns_http_400() -> None:
    response = client.post("/deploy-team", json=_valid_payload(team_id="rescue-hou-01"))

    assert response.status_code == 400
    assert "not available" in response.json()["detail"]


def test_successful_deployment_synchronizes_team_state() -> None:
    response = client.post("/deploy-team", json=_valid_payload())
    mission_id = response.json()["mission_id"]
    team = next(team for team in rescue_team_service._RESCUE_TEAMS if team.team_id == "rescue-ny-01")

    assert response.status_code == 201
    assert team.current_mission_id == mission_id
    assert team.availability == rescue_team_service.Availability.ASSIGNED


@pytest.mark.parametrize(
    "field, value",
    [("destination_latitude", 90.1), ("destination_longitude", 180.1)],
)
def test_invalid_request_coordinates_return_http_422(field: str, value: float) -> None:
    response = client.post("/deploy-team", json=_valid_payload(**{field: value}))

    assert response.status_code == 422


def test_missing_required_request_field_returns_http_422() -> None:
    payload = _valid_payload()
    payload.pop("team_id")

    response = client.post("/deploy-team", json=payload)

    assert response.status_code == 422


def test_deployment_returns_correct_http_status_code() -> None:
    response = client.post("/deploy-team", json=_valid_payload())

    assert response.status_code == 201