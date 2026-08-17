"""Pydantic models for emergency rescue missions.

This module defines the mission request/record model used by the
resource & rescue management domain. It contains validated data only and
no database or API logic.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class MissionStatus(str, Enum):
    """Lifecycle status for a rescue mission."""

    ASSIGNED = "ASSIGNED"
    DEPLOYED = "DEPLOYED"
    EN_ROUTE = "EN_ROUTE"
    ARRIVED = "ARRIVED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MissionPriority(str, Enum):
    """Priority level for a rescue mission."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Mission(BaseModel):
    """Represents an emergency rescue mission with location and operational state."""

    mission_id: str = Field(..., description="Unique mission identifier")
    disaster_id: str = Field(..., description="Disaster event associated with the mission")
    team_id: str = Field(..., description="Assigned rescue team identifier")
    hospital_id: str | None = Field(
        default=None,
        description="Associated hospital identifier, if applicable",
    )
    vehicle_id: str | None = Field(
        default=None,
        description="Assigned vehicle identifier, if applicable",
    )
    destination_latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Destination latitude in decimal degrees (-90 to 90)"
    )
    destination_longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Destination longitude in decimal degrees (-180 to 180)"
    )
    priority: MissionPriority = Field(..., description="Operational priority of the mission")
    status: MissionStatus = Field(..., description="Current lifecycle status of the mission")
    created_at: str = Field(
        ...,
        description="Timestamp for when the mission was created, as an ISO-8601 string",
    )
