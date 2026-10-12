"""Creation and read-only querying of operational audit events."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.rescue.models.audit_event import (
    AuditEventType,
    OperationalAuditEvent,
)
from backend.rescue.persistence import list_audit_events


def create_audit_event(
    event_type: AuditEventType,
    *,
    mission_id: str | None = None,
    disaster_id: str | None = None,
    resource_id: str | None = None,
    vehicle_id: str | None = None,
    detection_id: str | None = None,
    summary: dict[str, str | int | float | bool | None],
) -> OperationalAuditEvent:
    """Build one event with a generated ID and a UTC timestamp."""
    return OperationalAuditEvent(
        event_id=str(uuid4()),
        occurred_at=datetime.now(timezone.utc),
        event_type=event_type,
        actor="system/unspecified",
        mission_id=mission_id,
        disaster_id=disaster_id,
        resource_id=resource_id,
        vehicle_id=vehicle_id,
        detection_id=detection_id,
        summary=summary,
    )


def get_audit_events(
    *,
    limit: int,
    offset: int,
    mission_id: str | None = None,
    disaster_id: str | None = None,
    event_type: AuditEventType | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> tuple[list[OperationalAuditEvent], int]:
    """Query audit history in stable newest-first order."""
    return list_audit_events(
        limit=limit,
        offset=offset,
        mission_id=mission_id,
        disaster_id=disaster_id,
        event_type=event_type.value if event_type is not None else None,
        start_time=start_time.astimezone(timezone.utc).isoformat() if start_time else None,
        end_time=end_time.astimezone(timezone.utc).isoformat() if end_time else None,
    )
