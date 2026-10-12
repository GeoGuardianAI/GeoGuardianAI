"""Persistent operational audit-event model."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuditEventType(str, Enum):
    MISSION_CREATED = "MISSION_CREATED"
    MISSION_STATUS_CHANGED = "MISSION_STATUS_CHANGED"
    DETECTION_MISSION_LINKED = "DETECTION_MISSION_LINKED"
    RESOURCE_ALLOCATED = "RESOURCE_ALLOCATED"
    INVENTORY_ALLOCATED = "INVENTORY_ALLOCATED"
    RESOURCE_RELEASED = "RESOURCE_RELEASED"
    RESOURCE_CANCELLED = "RESOURCE_CANCELLED"
    RESOURCE_SETTLED_RELEASED = "RESOURCE_SETTLED_RELEASED"
    RESOURCE_SETTLED_CANCELLED = "RESOURCE_SETTLED_CANCELLED"
    VEHICLE_STATUS_CHANGED = "VEHICLE_STATUS_CHANGED"
    VEHICLE_LOCATION_CHANGED = "VEHICLE_LOCATION_CHANGED"


class OperationalAuditEvent(BaseModel):
    """A successful operational change with safe, structured change details."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(..., min_length=1)
    occurred_at: datetime
    event_type: AuditEventType
    actor: str = Field(default="system/unspecified", min_length=1)
    mission_id: str | None = None
    disaster_id: str | None = None
    resource_id: str | None = None
    vehicle_id: str | None = None
    detection_id: str | None = None
    summary: dict[str, str | int | float | bool | None]

    @field_validator("occurred_at")
    @classmethod
    def validate_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("occurred_at must be a UTC timestamp")
        return value
