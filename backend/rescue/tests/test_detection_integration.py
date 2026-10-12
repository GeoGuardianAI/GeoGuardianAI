"""Tests for the operator-confirmed detection adapter boundary."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from backend.rescue.main import app
from backend.rescue.models.detection_integration import (
    DetectionMissionLink,
    DisasterDetectionAdapter,
)
from backend.rescue.persistence import load_or_seed
from backend.rescue.services import (
    detection_integration_service,
    mission_service,
    rescue_team_service,
)

client = TestClient(app)

_ORIGINAL_MISSIONS = {
    mission_id: mission.model_copy(deep=True)
    for mission_id, mission in mission_service._MISSIONS.items()
}
_ORIGINAL_NEXT_MISSION_NUMBER = mission_service._NEXT_MISSION_NUMBER
_ORIGINAL_TEAMS = {
    team.team_id: team.model_copy(deep=True)
    for team in rescue_team_service._RESCUE_TEAMS
}
_ORIGINAL_DETECTION_LINKS = {
    detection_id: link.model_copy(deep=True)
    for detection_id, link in detection_integration_service._DETECTION_MISSION_LINKS.items()
}


@pytest.fixture(autouse=True)
def restore_service_state():
    mission_service._MISSIONS.clear()
    mission_service._MISSIONS.update(
        {
            mission_id: mission.model_copy(deep=True)
            for mission_id, mission in _ORIGINAL_MISSIONS.items()
        }
    )
    mission_service._NEXT_MISSION_NUMBER = _ORIGINAL_NEXT_MISSION_NUMBER
    rescue_team_service._RESCUE_TEAMS[:] = [
        team.model_copy(deep=True) for team in _ORIGINAL_TEAMS.values()
    ]
    detection_integration_service._DETECTION_MISSION_LINKS.clear()
    detection_integration_service._DETECTION_MISSION_LINKS.update(
        {
            detection_id: link.model_copy(deep=True)
            for detection_id, link in _ORIGINAL_DETECTION_LINKS.items()
        }
    )
    yield
    mission_service._MISSIONS.clear()
    mission_service._MISSIONS.update(
        {
            mission_id: mission.model_copy(deep=True)
            for mission_id, mission in _ORIGINAL_MISSIONS.items()
        }
    )
    mission_service._NEXT_MISSION_NUMBER = _ORIGINAL_NEXT_MISSION_NUMBER
    rescue_team_service._RESCUE_TEAMS[:] = [
        team.model_copy(deep=True) for team in _ORIGINAL_TEAMS.values()
    ]
    detection_integration_service._DETECTION_MISSION_LINKS.clear()
    detection_integration_service._DETECTION_MISSION_LINKS.update(
        {
            detection_id: link.model_copy(deep=True)
            for detection_id, link in _ORIGINAL_DETECTION_LINKS.items()
        }
    )


def _valid_payload(**detection_overrides):
    detection = {
        "detection_id": "member1-detection-unique-valid",
        "disaster_id": "flood-2026-001",
        "disaster_type": "flood",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "severity": 4,
        "confidence": 0.93,
        "affected_population": 1200,
        "critical_infrastructure": True,
    }
    request = {
        "detection": detection,
        "team_id": "rescue-ny-01",
        "priority": "HIGH",
        "confirmed": True,
    }
    for key, value in detection_overrides.items():
        if key in {"team_id", "priority", "confirmed"}:
            request[key] = value
        else:
            detection[key] = value
    return request


def test_confirmed_detection_maps_source_id_and_coordinates_to_mission() -> None:
    response = client.post(
        "/mission/from-detection", json=_valid_payload()
    )

    assert response.status_code == 201
    mission = response.json()
    assert mission["disaster_id"] == "flood-2026-001"
    assert mission["destination_latitude"] == 12.9716
    assert mission["destination_longitude"] == 77.5946
    assert mission["team_id"] == "rescue-ny-01"
    assert mission["priority"] == "HIGH"
    link = detection_integration_service.get_detection_mission_link(
        "member1-detection-unique-valid"
    )
    assert link is not None
    assert link.mission_id == mission["mission_id"]
    assert link.detection.confidence == 0.93
    persisted_links = load_or_seed("detection_links", [], DetectionMissionLink)
    assert any(
        persisted.detection_id == "member1-detection-unique-valid"
        and persisted.mission_id == mission["mission_id"]
        for persisted in persisted_links
    )


def test_detection_mission_requires_explicit_confirmation() -> None:
    original_missions = dict(mission_service._MISSIONS)

    response = client.post(
        "/mission/from-detection",
        json=_valid_payload(
            detection_id="member1-detection-unconfirmed", confirmed=False
        ),
    )

    assert response.status_code == 400
    assert "confirmation is required" in response.json()["detail"]
    assert mission_service._MISSIONS == original_missions


@pytest.mark.parametrize(
    "overrides",
    [
        {"latitude": None},
        {"longitude": None},
        {"latitude": 90.1},
        {"longitude": -180.1},
    ],
)
def test_missing_or_invalid_detection_coordinates_are_rejected(overrides) -> None:
    response = client.post(
        "/mission/from-detection", json=_valid_payload(**overrides)
    )

    assert response.status_code == 422


def test_duplicate_detection_id_cannot_create_a_second_mission() -> None:
    payload = _valid_payload(
        detection_id="member1-detection-duplicate-unique"
    )
    first = client.post("/mission/from-detection", json=payload)
    mission_count = len(mission_service._MISSIONS)
    second = client.post("/mission/from-detection", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert "already linked" in second.json()["detail"]
    assert len(mission_service._MISSIONS) == mission_count


def test_unknown_detection_fields_are_rejected() -> None:
    response = client.post(
        "/mission/from-detection",
        json=_valid_payload(
            detection_id="member1-detection-unknown-field",
            made_up_sensor_score=0.7,
        ),
    )

    assert response.status_code == 422


def test_failed_detection_link_write_rolls_back_mission_and_team(monkeypatch) -> None:
    detection = DisasterDetectionAdapter.model_validate(
        _valid_payload()["detection"]
    )
    team = next(
        team for team in rescue_team_service._RESCUE_TEAMS
        if team.team_id == "rescue-ny-01"
    )
    original_team_state = (team.availability, team.current_mission_id)
    original_missions = dict(mission_service._MISSIONS)

    monkeypatch.setattr(
        detection_integration_service,
        "persist_state",
        Mock(side_effect=OSError("simulated detection-link write failure")),
    )
    with pytest.raises(OSError, match="simulated detection-link write failure"):
        detection_integration_service.create_mission_from_detection(
            detection,
            team_id="rescue-ny-01",
            priority="HIGH",
            confirmed=True,
        )

    assert mission_service._MISSIONS == original_missions
    assert (team.availability, team.current_mission_id) == original_team_state
    assert (
        detection_integration_service.get_detection_mission_link(
            detection.detection_id
        )
        is None
    )
