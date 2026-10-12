"""Focused tests for persistent rescue-module state."""

import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

from backend.rescue import persistence
from backend.rescue.models.mission import Mission


def test_operational_state_survives_service_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "rescue.sqlite3"
    environment = os.environ.copy()
    environment["GEOGUARDIAN_DATABASE_PATH"] = str(database_path)
    project_root = Path(__file__).resolve().parents[3]
    create_state = textwrap.dedent(
        """
        from backend.rescue.services import (
            allocation_service,
            detection_integration_service,
            emergency_resource_service,
            emergency_vehicle_service,
            mission_service,
            shelter_service,
        )
        from backend.rescue.models.detection_integration import (
            DisasterDetectionAdapter,
        )

        mission = mission_service.create_mission(
            team_id="rescue-ny-01",
            disaster_id="persisted-disaster",
            destination_latitude=40.7128,
            destination_longitude=-74.0060,
        )
        allocation = allocation_service.allocate_resource_to_mission(
            mission.mission_id, "resource-food-ny-01", 25
        )
        mission_service.update_mission_status(mission.mission_id, "DEPLOYED")
        detection = DisasterDetectionAdapter(
            detection_id="restart-detection",
            disaster_id="persisted-detection-disaster",
            disaster_type="flood",
            latitude=12.9716,
            longitude=77.5946,
        )
        linked_mission = detection_integration_service.create_mission_from_detection(
            detection,
            team_id="rescue-la-01",
            priority="HIGH",
            confirmed=True,
        )
        emergency_vehicle_service.update_vehicle_status(
            "ambulance-blr-01", "IN_TRANSIT"
        )
        shelter_service.update_available_capacity("shelter-blr-01", 200)
        assert allocation.status.value == "ALLOCATED"
        assert linked_mission.mission_id == "mission-0002"
        assert emergency_resource_service.get_available_resources()[0].available_quantity > 0
        """
    )
    restore_state = textwrap.dedent(
        """
        from fastapi.testclient import TestClient

        from backend.rescue.services import (
            allocation_service,
            detection_integration_service,
            emergency_resource_service,
            emergency_vehicle_service,
            mission_service,
            rescue_team_service,
            shelter_service,
        )
        from backend.rescue.models.detection_integration import (
            DisasterDetectionAdapter,
        )
        from backend.rescue.services.detection_integration_service import (
            DuplicateDetectionError,
        )
        from backend.rescue.main import app

        missions = mission_service.list_missions()
        assert len(missions) == 2
        mission = missions[0]
        assert mission.mission_id == "mission-0001"
        assert mission.status.value == "DEPLOYED"
        assert mission.disaster_id == "persisted-disaster"
        detection_link = detection_integration_service.get_detection_mission_link(
            "restart-detection"
        )
        assert detection_link is not None
        assert detection_link.mission_id == "mission-0002"
        allocation = allocation_service.get_allocations_for_mission(mission.mission_id)[0]
        assert allocation.allocation_id == "allocation-0001"
        assert allocation.status.value == "ALLOCATED"
        resource = next(
            item for item in emergency_resource_service._RESOURCES
            if item.resource_id == allocation.resource_id
        )
        assert resource.available_quantity == 3175
        team = next(
            item for item in rescue_team_service._RESCUE_TEAMS
            if item.team_id == mission.team_id
        )
        assert team.current_mission_id == mission.mission_id
        assert emergency_vehicle_service.get_vehicle(
            "ambulance-blr-01"
        ).status.value == "IN_TRANSIT"
        assert shelter_service.get_emergency_shelter(
            "shelter-blr-01"
        ).available_capacity == 200
        assert len(emergency_resource_service._RESOURCES) == 6
        assert len(emergency_vehicle_service.get_vehicles()) == 6
        client = TestClient(app)
        assert client.get("/missions").json()[0]["mission_id"] == mission.mission_id
        assert client.get(
            f"/mission/{mission.mission_id}/allocations"
        ).json()[0]["status"] == "ALLOCATED"
        persisted_events = client.get(
            "/audit-events", params={"mission_id": mission.mission_id}
        ).json()
        assert persisted_events["total"] >= 3
        assert {
            event["event_type"] for event in persisted_events["items"]
        } >= {
            "MISSION_CREATED",
            "MISSION_STATUS_CHANGED",
            "RESOURCE_ALLOCATED",
        }
        linked_mission_events = client.get(
            "/audit-events", params={"mission_id": "mission-0002"}
        ).json()
        assert any(
            event["event_type"] == "DETECTION_MISSION_LINKED"
            and event["detection_id"] == "restart-detection"
            for event in linked_mission_events["items"]
        )
        assert client.get("/vehicles").json()[0]["vehicle_id"] == "ambulance-blr-01"
        assert len(client.get("/shelters").json()) == 4
        repeated_detection = DisasterDetectionAdapter(
            detection_id="restart-detection",
            disaster_id="persisted-detection-disaster",
            disaster_type="flood",
            latitude=12.9716,
            longitude=77.5946,
        )
        try:
            detection_integration_service.create_mission_from_detection(
                repeated_detection,
                team_id="rescue-miami-01",
                priority="HIGH",
                confirmed=True,
            )
        except DuplicateDetectionError:
            pass
        else:
            raise AssertionError("persisted detection ID was not deduplicated")
        assert mission_service.create_mission(
            team_id="rescue-miami-01",
            disaster_id="second-disaster",
            destination_latitude=12.9,
            destination_longitude=77.6,
        ).mission_id == "mission-0003"
        """
    )
    for script in (create_state, restore_state):
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr


def test_nested_database_writes_roll_back_on_outer_failure(tmp_path: Path) -> None:
    persistence.configure_database(tmp_path / "rollback.sqlite3")
    try:
        mission = Mission(
            mission_id="mission-rollback",
            disaster_id="rollback-disaster",
            team_id="rescue-ny-01",
            destination_latitude=40.7128,
            destination_longitude=-74.0060,
            priority="MEDIUM",
            status="ASSIGNED",
            created_at="2026-01-01T00:00:00+00:00",
        )
        with pytest.raises(RuntimeError, match="force rollback"):
            with persistence.transaction():
                persistence.persist_state({"missions": [mission]})
                raise RuntimeError("force rollback")

        assert persistence.load_or_seed("missions", [], Mission) == []
    finally:
        persistence.configure_database(":memory:")


def test_failed_mission_settlement_preserves_memory_and_database_state(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "settlement.sqlite3"
    environment = os.environ.copy()
    environment["GEOGUARDIAN_DATABASE_PATH"] = str(database_path)
    project_root = Path(__file__).resolve().parents[3]
    fail_settlement = textwrap.dedent(
        """
        from backend.rescue.services import (
            allocation_service,
            emergency_resource_service,
            mission_service,
            rescue_team_service,
        )

        mission = mission_service.create_mission(
            "rescue-ny-01", "rollback-disaster", 40.7128, -74.0060
        )
        allocation = allocation_service.allocate_resource_to_mission(
            mission.mission_id, "resource-food-ny-01", 50
        )
        mission_service.update_mission_status(mission.mission_id, "DEPLOYED")
        mission_service.update_mission_status(mission.mission_id, "EN_ROUTE")
        mission_service.update_mission_status(mission.mission_id, "ARRIVED")
        resource = next(
            item for item in emergency_resource_service._RESOURCES
            if item.resource_id == allocation.resource_id
        )
        quantity_before = resource.available_quantity

        def fail_write(_entities, *, audit_events=()):
            raise OSError("simulated SQLite write failure")

        mission_service.persist_state = fail_write
        try:
            mission_service.update_mission_status(mission.mission_id, "COMPLETED")
        except OSError as error:
            assert str(error) == "simulated SQLite write failure"
        else:
            raise AssertionError("expected settlement persistence to fail")

        assert mission.status.value == "ARRIVED"
        assert allocation.status.value == "ALLOCATED"
        assert resource.available_quantity == quantity_before
        team = next(
            item for item in rescue_team_service._RESCUE_TEAMS
            if item.team_id == mission.team_id
        )
        assert team.current_mission_id == mission.mission_id
        """
    )
    verify_durable_state = textwrap.dedent(
        """
        from backend.rescue.services import (
            allocation_service,
            emergency_resource_service,
            mission_service,
        )

        mission = mission_service.list_missions()[0]
        allocation = allocation_service.get_allocations_for_mission(
            mission.mission_id
        )[0]
        resource = next(
            item for item in emergency_resource_service._RESOURCES
            if item.resource_id == allocation.resource_id
        )
        assert mission.status.value == "ARRIVED"
        assert allocation.status.value == "ALLOCATED"
        assert resource.available_quantity == 3150
        """
    )
    for script in (fail_settlement, verify_durable_state):
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
