"""Concurrency regression tests for durable mission and inventory mutations."""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import sys
import textwrap
from threading import Barrier

from backend.rescue.models.audit_event import AuditEventType
from backend.rescue.models.allocation import ResourceAllocation
from backend.rescue.models.emergency_resource import EmergencyResource
from backend.rescue.models.mission import MissionStatus
from backend.rescue.persistence import (
    configure_database,
    load_records,
    persist_state,
    transaction,
)
from backend.rescue.services import (
    allocation_service,
    audit_service,
    emergency_resource_service,
    mission_service,
)


def _run_together(first, second):
    barrier = Barrier(2)

    def invoke(operation):
        barrier.wait()
        try:
            return operation()
        except ValueError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(invoke, first), executor.submit(invoke, second)]
        return [future.result(timeout=10) for future in futures]


def test_concurrent_mission_allocations_cannot_overspend_inventory() -> None:
    mission = mission_service.create_mission(
        "rescue-ny-01", "concurrent-allocation-disaster", 40.7128, -74.0060
    )
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    resource.available_quantity = 100
    persist_state({"resources": emergency_resource_service._RESOURCES})

    results = _run_together(
        lambda: allocation_service.allocate_resource_to_mission(
            mission.mission_id, resource.resource_id, 60
        ),
        lambda: allocation_service.allocate_resource_to_mission(
            mission.mission_id, resource.resource_id, 60
        ),
    )

    allocations = [
        result for result in results if not isinstance(result, ValueError)
    ]
    failures = [result for result in results if isinstance(result, ValueError)]
    assert len(allocations) == 1
    assert len(failures) == 1
    assert failures[0].args == ("requested quantity exceeds available quantity",)
    assert resource.available_quantity == 40
    assert len(
        allocation_service.get_allocations_for_mission(mission.mission_id)
    ) == 1
    events, _ = audit_service.get_audit_events(
        limit=100, offset=0, mission_id=mission.mission_id
    )
    assert sum(event.event_type == AuditEventType.RESOURCE_ALLOCATED for event in events) == 1


def test_racing_release_and_terminal_settlement_restore_inventory_once() -> None:
    mission = mission_service.create_mission(
        "rescue-ny-01", "concurrent-settlement-disaster", 40.7128, -74.0060
    )
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    resource.available_quantity = 100
    persist_state({"resources": emergency_resource_service._RESOURCES})
    allocation = allocation_service.allocate_resource_to_mission(
        mission.mission_id, resource.resource_id, 60
    )
    for status in (
        MissionStatus.DEPLOYED,
        MissionStatus.EN_ROUTE,
        MissionStatus.ARRIVED,
    ):
        mission_service.update_mission_status(mission.mission_id, status)

    results = _run_together(
        lambda: allocation_service.release_allocation(allocation.allocation_id),
        lambda: mission_service.update_mission_status(
            mission.mission_id, MissionStatus.COMPLETED
        ),
    )

    assert sum(not isinstance(result, ValueError) for result in results) >= 1
    assert resource.available_quantity == 100
    assert allocation_service._ALLOCATIONS[allocation.allocation_id].status.value == "RELEASED"
    assert mission_service.get_mission(mission.mission_id).status == MissionStatus.COMPLETED
    events, _ = audit_service.get_audit_events(
        limit=100, offset=0, mission_id=mission.mission_id
    )
    release_audits = [
        event
        for event in events
        if event.event_type
        in {
            AuditEventType.RESOURCE_RELEASED,
            AuditEventType.RESOURCE_SETTLED_RELEASED,
        }
        and event.summary.get("allocation_id") == allocation.allocation_id
    ]
    assert len(release_audits) == 1


def test_competing_mission_transitions_commit_only_one_valid_next_state() -> None:
    mission = mission_service.create_mission(
        "rescue-ny-01", "concurrent-transition-disaster", 40.7128, -74.0060
    )
    results = _run_together(
        lambda: mission_service.update_mission_status(
            mission.mission_id, MissionStatus.DEPLOYED
        ),
        lambda: mission_service.update_mission_status(
            mission.mission_id, MissionStatus.CANCELLED
        ),
    )

    successful = [result for result in results if not isinstance(result, ValueError)]
    assert len(successful) == 1
    persisted_mission = mission_service.get_mission(mission.mission_id)
    assert persisted_mission.status in {
        MissionStatus.DEPLOYED,
        MissionStatus.CANCELLED,
    }
    team = next(
        item
        for item in mission_service.rescue_team_service._RESCUE_TEAMS
        if item.team_id == mission.team_id
    )
    if persisted_mission.status == MissionStatus.DEPLOYED:
        assert team.current_mission_id == mission.mission_id
        assert team.availability.value == "DEPLOYED"
    else:
        assert team.current_mission_id is None
        assert team.availability.value == "AVAILABLE"
    events, _ = audit_service.get_audit_events(
        limit=100, offset=0, mission_id=mission.mission_id
    )
    transition_events = [
        event
        for event in events
        if event.event_type == AuditEventType.MISSION_STATUS_CHANGED
    ]
    assert len(transition_events) == 1
    assert transition_events[0].summary["to_status"] == persisted_mission.status.value


def test_concurrent_mission_creation_uses_unique_persisted_ids() -> None:
    results = _run_together(
        lambda: mission_service.create_mission(
            "rescue-ny-01", "concurrent-id-one", 40.7128, -74.0060
        ),
        lambda: mission_service.create_mission(
            "rescue-la-01", "concurrent-id-two", 34.0522, -118.2437
        ),
    )
    mission_ids = [mission.mission_id for mission in results]
    assert len(set(mission_ids)) == 2


def test_separate_processes_cannot_overspend_the_same_inventory(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "cross-process.sqlite3"
    gate_path = tmp_path / "start.txt"
    project_root = Path(__file__).resolve().parents[3]
    environment = os.environ.copy()
    environment["GEOGUARDIAN_DATABASE_PATH"] = str(database_path)
    configure_database(database_path)
    try:
        from backend.rescue.services import (
            emergency_vehicle_service,
            rescue_team_service,
            shelter_service,
        )

        persist_state(
            {
                "missions": list(mission_service._MISSIONS.values()),
                "resources": emergency_resource_service._RESOURCES,
                "allocations": list(allocation_service._ALLOCATIONS.values()),
                "vehicles": emergency_vehicle_service._VEHICLES,
                "rescue_teams": rescue_team_service._RESCUE_TEAMS,
                "shelters": shelter_service._SHELTERS,
                "emergency_shelters": shelter_service._EMERGENCY_SHELTERS,
            }
        )
        with transaction() as connection:
            resources = load_records(connection, "resources", EmergencyResource)
            target = next(
                item
                for item in resources
                if item.resource_id == "resource-food-ny-01"
            )
            target.available_quantity = 100
            persist_state({"resources": resources})
        mission = mission_service.create_mission(
            "rescue-ny-01", "cross-process-disaster", 40.7128, -74.0060
        )
        script = textwrap.dedent(
            f"""
            from pathlib import Path
            import time

            from backend.rescue.services.allocation_service import (
                allocate_resource_to_mission,
            )

            gate = Path({str(gate_path)!r})
            deadline = time.monotonic() + 20
            while not gate.exists():
                if time.monotonic() > deadline:
                    raise TimeoutError("test start gate was not opened")
                time.sleep(0.01)
            try:
                allocate_resource_to_mission(
                    {mission.mission_id!r}, "resource-food-ny-01", 60
                )
            except ValueError:
                print("rejected")
            else:
                print("allocated")
            """
        )
        processes = [
            subprocess.Popen(
                [sys.executable, "-c", script],
                cwd=project_root,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(2)
        ]
        gate_path.write_text("go", encoding="ascii")
        outputs = [process.communicate(timeout=30) for process in processes]
        assert all(process.returncode == 0 for process in processes), outputs
        outcomes = [stdout.strip() for stdout, _ in outputs]
        assert sorted(outcomes) == ["allocated", "rejected"]
        with transaction() as connection:
            persisted_resources = load_records(
                connection, "resources", EmergencyResource
            )
            persisted_allocations = load_records(
                connection, "allocations", ResourceAllocation
            )
        assert next(
            item
            for item in persisted_resources
            if item.resource_id == "resource-food-ny-01"
        ).available_quantity == 40
        assert len(
            [
                item
                for item in persisted_allocations
                if item.mission_id == mission.mission_id
            ]
        ) == 1
        persisted_events, _ = audit_service.get_audit_events(
            limit=100, offset=0, mission_id=mission.mission_id
        )
        assert sum(
            event.event_type == AuditEventType.RESOURCE_ALLOCATED
            for event in persisted_events
        ) == 1
    finally:
        configure_database(":memory:")
