"""Unit tests for the mission models."""

import pytest
from pydantic import ValidationError

from backend.rescue.models.mission import Mission, MissionPriority, MissionStatus


def test_all_valid_mission_status_values_are_accepted() -> None:
    for status in (
        MissionStatus.ASSIGNED,
        MissionStatus.DEPLOYED,
        MissionStatus.EN_ROUTE,
        MissionStatus.ARRIVED,
        MissionStatus.COMPLETED,
        MissionStatus.CANCELLED,
    ):
        assert isinstance(status, MissionStatus)


def test_all_valid_mission_priority_values_are_accepted() -> None:
    for priority in (
        MissionPriority.LOW,
        MissionPriority.MEDIUM,
        MissionPriority.HIGH,
        MissionPriority.CRITICAL,
    ):
        assert isinstance(priority, MissionPriority)


def test_valid_mission_can_be_created_with_all_required_fields() -> None:
    mission = Mission(
        mission_id="mission-0001",
        disaster_id="disaster-001",
        team_id="rescue-ny-01",
        hospital_id="nyc-central",
        vehicle_id="vehicle-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
        priority=MissionPriority.HIGH,
        status=MissionStatus.ASSIGNED,
        created_at="2026-08-17T12:00:00+00:00",
    )

    assert mission.mission_id == "mission-0001"
    assert mission.disaster_id == "disaster-001"
    assert mission.team_id == "rescue-ny-01"
    assert mission.hospital_id == "nyc-central"
    assert mission.vehicle_id == "vehicle-01"
    assert mission.priority == MissionPriority.HIGH
    assert mission.status == MissionStatus.ASSIGNED


def test_valid_mission_can_be_created_with_hospital_id_none() -> None:
    mission = Mission(
        mission_id="mission-0002",
        disaster_id="disaster-002",
        team_id="rescue-ny-01",
        hospital_id=None,
        vehicle_id="vehicle-02",
        destination_latitude=41.8781,
        destination_longitude=-87.6298,
        priority=MissionPriority.MEDIUM,
        status=MissionStatus.DEPLOYED,
        created_at="2026-08-17T12:10:00+00:00",
    )

    assert mission.hospital_id is None


def test_valid_mission_can_be_created_with_vehicle_id_none() -> None:
    mission = Mission(
        mission_id="mission-0003",
        disaster_id="disaster-003",
        team_id="rescue-miami-01",
        hospital_id="mia-health",
        vehicle_id=None,
        destination_latitude=25.7617,
        destination_longitude=-80.1918,
        priority=MissionPriority.LOW,
        status=MissionStatus.EN_ROUTE,
        created_at="2026-08-17T12:20:00+00:00",
    )

    assert mission.vehicle_id is None


def test_valid_mission_can_be_created_with_both_hospital_id_and_vehicle_id() -> None:
    mission = Mission(
        mission_id="mission-0004",
        disaster_id="disaster-004",
        team_id="rescue-la-01",
        hospital_id="la-metro",
        vehicle_id="vehicle-03",
        destination_latitude=34.0522,
        destination_longitude=-118.2437,
        priority=MissionPriority.CRITICAL,
        status=MissionStatus.ARRIVED,
        created_at="2026-08-17T12:30:00+00:00",
    )

    assert mission.hospital_id == "la-metro"
    assert mission.vehicle_id == "vehicle-03"


def test_destination_latitude_negative_90_is_accepted() -> None:
    mission = Mission(
        mission_id="mission-0005",
        disaster_id="disaster-005",
        team_id="rescue-ny-01",
        destination_latitude=-90.0,
        destination_longitude=0.0,
        priority=MissionPriority.MEDIUM,
        status=MissionStatus.ASSIGNED,
        created_at="2026-08-17T12:40:00+00:00",
    )

    assert mission.destination_latitude == -90.0


def test_destination_latitude_positive_90_is_accepted() -> None:
    mission = Mission(
        mission_id="mission-0006",
        disaster_id="disaster-006",
        team_id="rescue-ny-01",
        destination_latitude=90.0,
        destination_longitude=0.0,
        priority=MissionPriority.MEDIUM,
        status=MissionStatus.ASSIGNED,
        created_at="2026-08-17T12:50:00+00:00",
    )

    assert mission.destination_latitude == 90.0


def test_destination_longitude_negative_180_is_accepted() -> None:
    mission = Mission(
        mission_id="mission-0007",
        disaster_id="disaster-007",
        team_id="rescue-ny-01",
        destination_latitude=0.0,
        destination_longitude=-180.0,
        priority=MissionPriority.MEDIUM,
        status=MissionStatus.ASSIGNED,
        created_at="2026-08-17T13:00:00+00:00",
    )

    assert mission.destination_longitude == -180.0


def test_destination_longitude_positive_180_is_accepted() -> None:
    mission = Mission(
        mission_id="mission-0008",
        disaster_id="disaster-008",
        team_id="rescue-ny-01",
        destination_latitude=0.0,
        destination_longitude=180.0,
        priority=MissionPriority.MEDIUM,
        status=MissionStatus.ASSIGNED,
        created_at="2026-08-17T13:10:00+00:00",
    )

    assert mission.destination_longitude == 180.0


def test_destination_latitude_greater_than_90_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Mission(
            mission_id="mission-0009",
            disaster_id="disaster-009",
            team_id="rescue-ny-01",
            destination_latitude=90.1,
            destination_longitude=0.0,
            priority=MissionPriority.MEDIUM,
            status=MissionStatus.ASSIGNED,
            created_at="2026-08-17T13:20:00+00:00",
        )


def test_destination_latitude_less_than_negative_90_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Mission(
            mission_id="mission-0010",
            disaster_id="disaster-010",
            team_id="rescue-ny-01",
            destination_latitude=-90.1,
            destination_longitude=0.0,
            priority=MissionPriority.MEDIUM,
            status=MissionStatus.ASSIGNED,
            created_at="2026-08-17T13:30:00+00:00",
        )


def test_destination_longitude_greater_than_180_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Mission(
            mission_id="mission-0011",
            disaster_id="disaster-011",
            team_id="rescue-ny-01",
            destination_latitude=0.0,
            destination_longitude=180.1,
            priority=MissionPriority.MEDIUM,
            status=MissionStatus.ASSIGNED,
            created_at="2026-08-17T13:40:00+00:00",
        )


def test_destination_longitude_less_than_negative_180_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Mission(
            mission_id="mission-0012",
            disaster_id="disaster-012",
            team_id="rescue-ny-01",
            destination_latitude=0.0,
            destination_longitude=-180.1,
            priority=MissionPriority.MEDIUM,
            status=MissionStatus.ASSIGNED,
            created_at="2026-08-17T13:50:00+00:00",
        )


def test_invalid_priority_values_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Mission(
            mission_id="mission-0013",
            disaster_id="disaster-013",
            team_id="rescue-ny-01",
            destination_latitude=0.0,
            destination_longitude=0.0,
            priority="URGENT",
            status=MissionStatus.ASSIGNED,
            created_at="2026-08-17T14:00:00+00:00",
        )


def test_invalid_status_values_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Mission(
            mission_id="mission-0014",
            disaster_id="disaster-014",
            team_id="rescue-ny-01",
            destination_latitude=0.0,
            destination_longitude=0.0,
            priority=MissionPriority.MEDIUM,
            status="UNKNOWN",
            created_at="2026-08-17T14:10:00+00:00",
        )


def test_valid_created_at_string_is_accepted() -> None:
    mission = Mission(
        mission_id="mission-0015",
        disaster_id="disaster-015",
        team_id="rescue-ny-01",
        destination_latitude=0.0,
        destination_longitude=0.0,
        priority=MissionPriority.MEDIUM,
        status=MissionStatus.ASSIGNED,
        created_at="2026-08-17T14:20:00+00:00",
    )

    assert mission.created_at == "2026-08-17T14:20:00+00:00"


def test_model_preserves_all_values_correctly() -> None:
    mission = Mission(
        mission_id="mission-0016",
        disaster_id="disaster-016",
        team_id="rescue-ny-02",
        hospital_id="nyc-central",
        vehicle_id="vehicle-99",
        destination_latitude=39.7392,
        destination_longitude=-104.9903,
        priority=MissionPriority.CRITICAL,
        status=MissionStatus.DEPLOYED,
        created_at="2026-08-17T14:30:00+00:00",
    )

    assert mission.mission_id == "mission-0016"
    assert mission.disaster_id == "disaster-016"
    assert mission.team_id == "rescue-ny-02"
    assert mission.hospital_id == "nyc-central"
    assert mission.vehicle_id == "vehicle-99"
    assert mission.destination_latitude == 39.7392
    assert mission.destination_longitude == -104.9903
    assert mission.priority == MissionPriority.CRITICAL
    assert mission.status == MissionStatus.DEPLOYED
    assert mission.created_at == "2026-08-17T14:30:00+00:00"
