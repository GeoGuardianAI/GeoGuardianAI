"""Unit tests for the in-memory mission service."""

import pytest

import backend.rescue.services.mission_service as mission_service
import backend.rescue.services.rescue_team_service as rescue_team_service
from backend.rescue.models.mission import Mission, MissionPriority, MissionStatus
from backend.rescue.models.rescue_team import Availability


_ORIGINAL_TEAM_STATE = {
    team.team_id: {
        "availability": team.availability,
        "current_mission_id": team.current_mission_id,
    }
    for team in rescue_team_service._RESCUE_TEAMS
}
_ORIGINAL_MISSION_STATE = {
    mission_id: mission.model_copy(deep=True)
    for mission_id, mission in mission_service._MISSIONS.items()
}
_ORIGINAL_NEXT_MISSION_NUMBER = mission_service._NEXT_MISSION_NUMBER


def _restore_team_state() -> None:
    for team in rescue_team_service._RESCUE_TEAMS:
        original = _ORIGINAL_TEAM_STATE.get(team.team_id)
        if original is None:
            team.availability = Availability.AVAILABLE
            team.current_mission_id = None
            continue

        team.availability = original["availability"]
        team.current_mission_id = original["current_mission_id"]


@pytest.fixture(autouse=True)
def reset_service_state() -> None:
    """Reset the mission service and shared rescue-team state before and after each test."""
    _restore_team_state()
    mission_service._MISSIONS.clear()
    mission_service._MISSIONS.update({
        mission_id: mission.model_copy(deep=True)
        for mission_id, mission in _ORIGINAL_MISSION_STATE.items()
    })
    mission_service._NEXT_MISSION_NUMBER = _ORIGINAL_NEXT_MISSION_NUMBER

    yield

    mission_service._MISSIONS.clear()
    mission_service._MISSIONS.update({
        mission_id: mission.model_copy(deep=True)
        for mission_id, mission in _ORIGINAL_MISSION_STATE.items()
    })
    mission_service._NEXT_MISSION_NUMBER = _ORIGINAL_NEXT_MISSION_NUMBER
    _restore_team_state()


def test_create_mission_for_available_team_succeeds() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    assert isinstance(mission, Mission)


def test_create_mission_returns_mission_instance() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    assert isinstance(mission, Mission)


def test_created_mission_has_requested_disaster_id() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    assert mission.disaster_id == "disaster-01"


def test_created_mission_has_requested_team_id() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    assert mission.team_id == "rescue-ny-01"


def test_created_mission_has_requested_destination_coordinates() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    assert mission.destination_latitude == 40.7128
    assert mission.destination_longitude == -74.0060


def test_requested_priority_is_preserved() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
        priority=MissionPriority.CRITICAL,
    )

    assert mission.priority == MissionPriority.CRITICAL


def test_default_hospital_id_is_none() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    assert mission.hospital_id is None


def test_default_vehicle_id_is_none() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    assert mission.vehicle_id is None


def test_initial_mission_status_is_assigned() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    assert mission.status == MissionStatus.ASSIGNED


def test_mission_id_is_automatically_generated() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    assert mission.mission_id.startswith("mission-")


def test_created_at_is_populated() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    assert isinstance(mission.created_at, str)
    assert mission.created_at.strip() != ""


def test_created_mission_can_be_retrieved_with_get_mission() -> None:
    created = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    fetched = mission_service.get_mission(created.mission_id)

    assert fetched == created


def test_creating_mission_updates_team_current_mission_id() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    team = next(team for team in rescue_team_service._RESCUE_TEAMS if team.team_id == "rescue-ny-01")

    assert team.current_mission_id == mission.mission_id


def test_creating_mission_changes_team_availability_from_available_to_assigned() -> None:
    mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    team = next(team for team in rescue_team_service._RESCUE_TEAMS if team.team_id == "rescue-ny-01")

    assert team.availability == Availability.ASSIGNED


def test_creating_mission_for_nonexistent_team_raises_value_error() -> None:
    with pytest.raises(ValueError, match="does not exist"):
        mission_service.create_mission(
            team_id="missing-team",
            disaster_id="disaster-01",
            destination_latitude=40.7128,
            destination_longitude=-74.0060,
        )


def test_creating_mission_for_unavailable_team_raises_value_error() -> None:
    with pytest.raises(ValueError, match="not available"):
        mission_service.create_mission(
            team_id="rescue-hou-01",
            disaster_id="disaster-01",
            destination_latitude=40.7128,
            destination_longitude=-74.0060,
        )


def test_team_already_assigned_deployed_or_unavailable_cannot_receive_another_mission() -> None:
    for team_id in ("rescue-hou-01", "rescue-sea-01", "rescue-den-01"):
        with pytest.raises(ValueError):
            mission_service.create_mission(
                team_id=team_id,
                disaster_id="disaster-01",
                destination_latitude=40.7128,
                destination_longitude=-74.0060,
            )


def test_get_mission_returns_existing_mission() -> None:
    created = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    assert mission_service.get_mission(created.mission_id) == created


def test_get_mission_for_unknown_id_raises_value_error() -> None:
    with pytest.raises(ValueError, match="does not exist"):
        mission_service.get_mission("unknown-id")


def test_assigned_to_deployed_is_allowed() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    updated = mission_service.update_mission_status(mission.mission_id, MissionStatus.DEPLOYED)

    assert updated.status == MissionStatus.DEPLOYED


def test_deployed_to_en_route_is_allowed() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )
    mission_service.update_mission_status(mission.mission_id, MissionStatus.DEPLOYED)

    updated = mission_service.update_mission_status(mission.mission_id, MissionStatus.EN_ROUTE)

    assert updated.status == MissionStatus.EN_ROUTE


def test_en_route_to_arrived_is_allowed() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )
    mission_service.update_mission_status(mission.mission_id, MissionStatus.DEPLOYED)
    mission_service.update_mission_status(mission.mission_id, MissionStatus.EN_ROUTE)

    updated = mission_service.update_mission_status(mission.mission_id, MissionStatus.ARRIVED)

    assert updated.status == MissionStatus.ARRIVED


def test_arrived_to_completed_is_allowed() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )
    mission_service.update_mission_status(mission.mission_id, MissionStatus.DEPLOYED)
    mission_service.update_mission_status(mission.mission_id, MissionStatus.EN_ROUTE)
    mission_service.update_mission_status(mission.mission_id, MissionStatus.ARRIVED)

    updated = mission_service.update_mission_status(mission.mission_id, MissionStatus.COMPLETED)

    assert updated.status == MissionStatus.COMPLETED


def test_assigned_to_cancelled_is_allowed() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    updated = mission_service.update_mission_status(mission.mission_id, MissionStatus.CANCELLED)

    assert updated.status == MissionStatus.CANCELLED


def test_invalid_status_transitions_raise_value_error() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    with pytest.raises(ValueError):
        mission_service.update_mission_status(mission.mission_id, MissionStatus.COMPLETED)


def test_updating_nonexistent_mission_raises_value_error() -> None:
    with pytest.raises(ValueError, match="does not exist"):
        mission_service.update_mission_status("missing-id", MissionStatus.DEPLOYED)


def test_updating_status_preserves_other_fields() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
        priority=MissionPriority.HIGH,
        hospital_id="nyc-central",
        vehicle_id="vehicle-01",
    )

    updated = mission_service.update_mission_status(mission.mission_id, MissionStatus.DEPLOYED)

    assert updated.mission_id == mission.mission_id
    assert updated.disaster_id == mission.disaster_id
    assert updated.team_id == mission.team_id
    assert updated.hospital_id == mission.hospital_id
    assert updated.vehicle_id == mission.vehicle_id
    assert updated.destination_latitude == mission.destination_latitude
    assert updated.destination_longitude == mission.destination_longitude
    assert updated.priority == mission.priority
    assert updated.created_at == mission.created_at


def test_mission_status_is_changed_after_valid_update() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    mission_service.update_mission_status(mission.mission_id, MissionStatus.DEPLOYED)

    assert mission_service.get_mission(mission.mission_id).status == MissionStatus.DEPLOYED


def test_team_remains_not_available_while_mission_is_active() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    mission_service.update_mission_status(mission.mission_id, MissionStatus.DEPLOYED)
    team = next(team for team in rescue_team_service._RESCUE_TEAMS if team.team_id == "rescue-ny-01")

    assert team.availability == Availability.DEPLOYED


def test_completing_mission_makes_team_available_again() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )
    mission_service.update_mission_status(mission.mission_id, MissionStatus.DEPLOYED)
    mission_service.update_mission_status(mission.mission_id, MissionStatus.EN_ROUTE)
    mission_service.update_mission_status(mission.mission_id, MissionStatus.ARRIVED)
    mission_service.update_mission_status(mission.mission_id, MissionStatus.COMPLETED)

    team = next(team for team in rescue_team_service._RESCUE_TEAMS if team.team_id == "rescue-ny-01")

    assert team.availability == Availability.AVAILABLE


def test_cancelling_mission_makes_team_available_again() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    mission_service.update_mission_status(mission.mission_id, MissionStatus.CANCELLED)
    team = next(team for team in rescue_team_service._RESCUE_TEAMS if team.team_id == "rescue-ny-01")

    assert team.availability == Availability.AVAILABLE


def test_current_mission_id_is_cleared_when_mission_reaches_terminal_state() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )
    mission_service.update_mission_status(mission.mission_id, MissionStatus.CANCELLED)

    team = next(team for team in rescue_team_service._RESCUE_TEAMS if team.team_id == "rescue-ny-01")

    assert team.current_mission_id is None


def test_valid_string_status_value_is_accepted() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    updated = mission_service.update_mission_status(mission.mission_id, "DEPLOYED")

    assert updated.status == MissionStatus.DEPLOYED


def test_valid_mission_status_enum_is_accepted() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    updated = mission_service.update_mission_status(mission.mission_id, MissionStatus.DEPLOYED)

    assert updated.status == MissionStatus.DEPLOYED


def test_valid_mission_priority_enum_is_accepted() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
        priority=MissionPriority.HIGH,
    )

    assert mission.priority == MissionPriority.HIGH


def test_invalid_status_value_raises_value_error() -> None:
    with pytest.raises(ValueError):
        mission_service.create_mission(
            team_id="rescue-ny-01",
            disaster_id="disaster-01",
            destination_latitude=40.7128,
            destination_longitude=-74.0060,
            status="INVALID",
        )


def test_invalid_priority_value_raises_value_error() -> None:
    with pytest.raises(ValueError):
        mission_service.create_mission(
            team_id="rescue-ny-01",
            disaster_id="disaster-01",
            destination_latitude=40.7128,
            destination_longitude=-74.0060,
            priority="INVALID",
        )


def test_two_missions_receive_different_ids() -> None:
    first = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )
    second = mission_service.create_mission(
        team_id="rescue-miami-01",
        disaster_id="disaster-02",
        destination_latitude=25.7617,
        destination_longitude=-80.1918,
    )

    assert first.mission_id != second.mission_id


def test_created_mission_remains_retrievable_from_in_memory_store() -> None:
    created = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    assert created.mission_id in mission_service._MISSIONS
    assert mission_service._MISSIONS[created.mission_id] == created


def test_service_does_not_require_external_database_or_http_service() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-01",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    assert isinstance(mission, Mission)
    assert mission.mission_id in mission_service._MISSIONS
