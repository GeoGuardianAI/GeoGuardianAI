"""Pydantic models for the rescue module: rescue team definitions.

This module defines the `RescueTeam` model used to represent rescue-team
location, composition, and availability for the Resource & Rescue Management
component. It uses Pydantic v2 `BaseModel` with enum-backed status values and
field constraints for geographic and team attributes.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class TeamType(str, Enum):
    """Operational category for a rescue team."""

    SEARCH_AND_RESCUE = "SEARCH_AND_RESCUE"
    MEDICAL = "MEDICAL"
    FIRE_AND_RESCUE = "FIRE_AND_RESCUE"
    WATER_RESCUE = "WATER_RESCUE"
    DISASTER_RESPONSE = "DISASTER_RESPONSE"


class Availability(str, Enum):
    """Current availability state of a rescue team."""

    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    DEPLOYED = "DEPLOYED"
    UNAVAILABLE = "UNAVAILABLE"


class RescueTeam(BaseModel):
    """Represents a rescue team with operational status and geographic context."""

    team_id: str = Field(..., description="Unique rescue team identifier")
    name: str = Field(..., description="Human-readable rescue team name")
    team_type: TeamType = Field(
        ..., description="Operational classification for the team"
    )

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude in decimal degrees (-90 to 90)",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude in decimal degrees (-180 to 180)",
    )

    members: int = Field(..., ge=0, description="Number of team members (>= 0)")
    specialization: list[str] = Field(
        ...,
        description="List of technical or operational skills or specialties",
    )
    availability: Availability = Field(
        ..., description="Current operational availability state"
    )
    current_mission_id: str | None = Field(
        default=None,
        description="Identifier for the mission currently assigned to the team, if any",
    )

    @field_validator("specialization")
    @classmethod
    def validate_specialization(cls, value: list[str]) -> list[str]:
        """Ensure specialization is a list containing only string values."""
        if not isinstance(value, list):
            raise TypeError("specialization must be a list of strings")
        if not all(isinstance(item, str) for item in value):
            raise TypeError("specialization must be a list of strings")
        return value
