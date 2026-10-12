"""Read-only paginated access to operational audit history."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.rescue.models.audit_event import (
    AuditEventType,
    OperationalAuditEvent,
)
from backend.rescue.services.audit_service import get_audit_events

router = APIRouter()


class AuditEventPage(BaseModel):
    """One bounded audit-event page and its matching record count."""

    items: list[OperationalAuditEvent]
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1, le=100)
    offset: int = Field(..., ge=0)


@router.get(
    "/audit-events",
    response_model=AuditEventPage,
    summary="Read operational audit history",
    tags=["Audit"],
)
def audit_events(
    mission_id: str | None = Query(default=None, min_length=1),
    disaster_id: str | None = Query(default=None, min_length=1),
    event_type: AuditEventType | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AuditEventPage:
    """Return newest-first events, with event ID as deterministic tie-breaker."""
    if mission_id is not None and not mission_id.strip():
        raise HTTPException(status_code=422, detail="mission_id must not be blank")
    if disaster_id is not None and not disaster_id.strip():
        raise HTTPException(status_code=422, detail="disaster_id must not be blank")
    if start_time is not None and start_time.tzinfo is None:
        raise HTTPException(status_code=422, detail="start_time must include a timezone")
    if end_time is not None and end_time.tzinfo is None:
        raise HTTPException(status_code=422, detail="end_time must include a timezone")
    if start_time is not None and end_time is not None and start_time > end_time:
        raise HTTPException(status_code=422, detail="start_time must not be after end_time")

    items, total = get_audit_events(
        limit=limit,
        offset=offset,
        mission_id=mission_id,
        disaster_id=disaster_id,
        event_type=event_type,
        start_time=start_time,
        end_time=end_time,
    )
    return AuditEventPage(items=items, total=total, limit=limit, offset=offset)
