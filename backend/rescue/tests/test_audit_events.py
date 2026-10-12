"""Tests for transactional operational audit-event recording and queries."""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import subprocess
import sys
import textwrap
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.rescue.main import app
from backend.rescue.models.audit_event import AuditEventType
from backend.rescue.persistence import persist_state, transaction
from backend.rescue.services import (
    allocation_service,
    audit_service,
    emergency_vehicle_service,
    mission_service,
)

client = TestClient(app)


def _unique_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def _insert_test_event(
    *,
    mission_id: str,
    disaster_id: str,
    event_type: AuditEventType = AuditEventType.MISSION_CREATED,
    occurred_at: datetime | None = None,
) -> None:
    event = audit_service.create_audit_event(
        event_type,
        mission_id=mission_id,
        disaster_id=disaster_id,
        summary={"test_event": True},
    )
    if occurred_at is not None:
        event.occurred_at = occurred_at
    persist_state({}, audit_events=[event])


def test_mission_and_resource_actions_write_transactional_audit_events() -> None:
    disaster_id = _unique_id("audit-disaster")
    mission = mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id=disaster_id,
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )
    created_events, _ = audit_service.get_audit_events(
        limit=100, offset=0, disaster_id=disaster_id
    )
    assert len(created_events) == 1
    assert created_events[0].event_type == AuditEventType.MISSION_CREATED
    assert created_events[0].actor == "system/unspecified"
    assert created_events[0].occurred_at.tzinfo is not None
    assert created_events[0].summary["status"] == "ASSIGNED"

    allocation = allocation_service.allocate_resource_to_mission(
        mission.mission_id, "resource-food-ny-01", 12
    )
    allocation_service.release_allocation(allocation.allocation_id)
    history, _ = audit_service.get_audit_events(
        limit=100, offset=0, disaster_id=disaster_id
    )
    types = {event.event_type for event in history}
    assert AuditEventType.RESOURCE_ALLOCATED in types
    assert AuditEventType.RESOURCE_RELEASED in types


def test_terminal_status_records_status_and_automatic_settlement_events() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-la-01",
        disaster_id=_unique_id("audit-terminal"),
        destination_latitude=34.0522,
        destination_longitude=-118.2437,
    )
    allocation = allocation_service.allocate_resource_to_mission(
        mission.mission_id, "resource-food-ny-01", 7
    )
    for status in ("DEPLOYED", "EN_ROUTE", "ARRIVED"):
        mission_service.update_mission_status(mission.mission_id, status)
    mission_service.update_mission_status(mission.mission_id, "COMPLETED")

    events, _ = audit_service.get_audit_events(
        limit=100, offset=0, disaster_id=mission.disaster_id
    )
    assert sum(
        event.event_type == AuditEventType.RESOURCE_SETTLED_RELEASED
        and event.summary["allocation_id"] == allocation.allocation_id
        for event in events
    ) == 1
    assert any(
        event.event_type == AuditEventType.MISSION_STATUS_CHANGED
        and event.summary["to_status"] == "COMPLETED"
        for event in events
    )


def test_cancellation_and_vehicle_changes_are_audited(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment["GEOGUARDIAN_DATABASE_PATH"] = str(tmp_path / "audit-ops.sqlite3")
    project_root = Path(__file__).resolve().parents[3]
    script = textwrap.dedent(
        """
        from uuid import uuid4

        from backend.rescue.models.audit_event import AuditEventType
        from backend.rescue.services import (
            allocation_service,
            audit_service,
            emergency_vehicle_service,
            mission_service,
        )

        team_id = "rescue-ny-01"
        manual = mission_service.create_mission(
            team_id, f"manual-cancel-{uuid4().hex}", 40.7128, -74.0060
        )
        manual_allocation = allocation_service.allocate_resource_to_mission(
            manual.mission_id, "resource-food-ny-01", 3
        )
        allocation_service.cancel_allocation(manual_allocation.allocation_id)
        mission_service.update_mission_status(manual.mission_id, "CANCELLED")
        manual_events, _ = audit_service.get_audit_events(
            limit=100, offset=0, disaster_id=manual.disaster_id
        )
        assert any(
            event.event_type == AuditEventType.RESOURCE_CANCELLED
            and event.summary["allocation_id"] == manual_allocation.allocation_id
            for event in manual_events
        )

        mission = mission_service.create_mission(
            team_id, f"auto-cancel-{uuid4().hex}", 40.7128, -74.0060
        )
        allocation = allocation_service.allocate_resource_to_mission(
            mission.mission_id, "resource-food-ny-01", 4
        )
        mission_service.update_mission_status(mission.mission_id, "CANCELLED")
        cancellation_events, _ = audit_service.get_audit_events(
            limit=100, offset=0, disaster_id=mission.disaster_id
        )
        assert any(
            event.event_type == AuditEventType.RESOURCE_SETTLED_CANCELLED
            and event.summary["allocation_id"] == allocation.allocation_id
            for event in cancellation_events
        )

        vehicle_id = "ambulance-blr-01"
        emergency_vehicle_service.update_vehicle_status(vehicle_id, "IN_TRANSIT")
        emergency_vehicle_service.update_vehicle_location(vehicle_id, 12.98, 77.61)
        vehicle_events, _ = audit_service.get_audit_events(limit=1000, offset=0)
        assert any(
            event.event_type == AuditEventType.VEHICLE_STATUS_CHANGED
            and event.vehicle_id == vehicle_id
            for event in vehicle_events
        )
        assert any(
            event.event_type == AuditEventType.VEHICLE_LOCATION_CHANGED
            and event.vehicle_id == vehicle_id
            for event in vehicle_events
        )
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_audit_filters_and_pagination_are_validated_and_deterministic() -> None:
    mission_id = _unique_id("audit-page")
    disaster_id = _unique_id("audit-filter")
    timestamp = datetime.now(timezone.utc).replace(microsecond=0)
    for _ in range(3):
        _insert_test_event(
            mission_id=mission_id,
            disaster_id=disaster_id,
            occurred_at=timestamp,
        )

    first = client.get(
        "/audit-events",
        params={"mission_id": mission_id, "limit": 2, "offset": 0},
    )
    second = client.get(
        "/audit-events",
        params={"mission_id": mission_id, "limit": 2, "offset": 2},
    )
    assert first.status_code == second.status_code == 200
    first_data = first.json()
    second_data = second.json()
    assert first_data["total"] == 3
    assert len(first_data["items"]) == 2
    assert len(second_data["items"]) == 1
    assert first_data["items"][0]["event_id"] > first_data["items"][1]["event_id"]
    assert first_data["items"][1]["event_id"] > second_data["items"][0]["event_id"]

    filtered = client.get(
        "/audit-events",
        params={
            "disaster_id": disaster_id,
            "event_type": "MISSION_CREATED",
            "start_time": (timestamp - timedelta(seconds=1)).isoformat(),
            "end_time": (timestamp + timedelta(seconds=1)).isoformat(),
        },
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 3
    assert client.get(
        "/audit-events", params={"event_type": "NOT_A_REAL_EVENT"}
    ).status_code == 422
    assert client.get(
        "/audit-events",
        params={
            "start_time": (timestamp + timedelta(seconds=1)).isoformat(),
            "end_time": timestamp.isoformat(),
        },
    ).status_code == 422
    assert client.get(
        "/audit-events", params={"start_time": "2026-10-12T00:00:00"}
    ).status_code == 422
    assert client.get("/audit-events", params={"limit": 101}).status_code == 422


def test_audit_event_rolls_back_with_outer_transaction() -> None:
    mission_id = _unique_id("audit-rollback")
    event = audit_service.create_audit_event(
        AuditEventType.MISSION_CREATED,
        mission_id=mission_id,
        summary={"status": "ASSIGNED"},
    )
    with pytest.raises(RuntimeError, match="abort operational write"):
        with transaction():
            persist_state({}, audit_events=[event])
            raise RuntimeError("abort operational write")

    events, total = audit_service.get_audit_events(
        limit=10, offset=0, mission_id=mission_id
    )
    assert events == []
    assert total == 0


def test_failed_operational_actions_do_not_create_success_events() -> None:
    mission = mission_service.create_mission(
        team_id="rescue-chi-01",
        disaster_id=_unique_id("audit-failed-disaster"),
        destination_latitude=41.8781,
        destination_longitude=-87.6298,
    )
    before, _ = audit_service.get_audit_events(
        limit=100, offset=0, disaster_id=mission.disaster_id
    )
    with pytest.raises(ValueError):
        mission_service.update_mission_status(mission.mission_id, "COMPLETED")
    with pytest.raises(ValueError):
        allocation_service.allocate_resource_to_mission(
            mission.mission_id, "resource-food-ny-01", 999999
        )
    with pytest.raises(ValueError):
        emergency_vehicle_service.update_vehicle_status(
            "missing-audit-vehicle", "AVAILABLE"
        )
    after, _ = audit_service.get_audit_events(
        limit=100, offset=0, disaster_id=mission.disaster_id
    )
    assert len(after) == len(before)
    assert mission.status.value == "ASSIGNED"
