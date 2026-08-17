"""Pydantic models for disaster resource allocation requests and recommendations.

These models define the validated payload used to describe a disaster event and
represent a recommendation for the best matching hospital and rescue team.
They are intentionally data-only and do not include business logic.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from backend.rescue.models.hospital import Hospital
from backend.rescue.models.rescue_team import RescueTeam


class AllocationRequest(BaseModel):
    """Represents a disaster event requesting resource recommendations."""

    disaster_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the disaster event; must not be empty",
    )
    disaster_type: str = Field(
        ...,
        min_length=1,
        description="Type or category of disaster; must not be empty",
    )
    latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Latitude in decimal degrees (-90 to 90)"
    )
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude in decimal degrees (-180 to 180)"
    )
    severity: int = Field(
        ...,
        ge=1,
        le=5,
        description="Disaster severity on a 1-5 scale",
    )
    required_specialization: str | None = Field(
        default=None,
        description="Optional rescue specialization required for a recommended team",
    )

    @field_validator("disaster_id", "disaster_type")
    @classmethod
    def _validate_nonempty_text(cls, value: str) -> str:
        """Reject empty or whitespace-only text fields."""
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value


class AllocationRecommendation(BaseModel):
    """Represents a recommendation for hospital and rescue-team alignment."""

    disaster_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of the disaster event associated with the recommendation",
    )
    recommended_hospital: Hospital = Field(
        ..., description="Nearest or most suitable hospital recommendation for the event"
    )
    recommended_rescue_team: RescueTeam = Field(
        ..., description="Best available rescue team recommendation for the event"
    )
    priority_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Priority score for the recommendation, normalized to a 0-100 scale",
    )
    estimated_distance_km: float = Field(
        ...,
        ge=0.0,
        description="Estimated distance in kilometers between the disaster site and the recommendation",
    )
    reasoning: str = Field(
        ...,
        min_length=1,
        description="Human-readable explanation for the recommendation",
    )

    @field_validator("disaster_id", "reasoning")
    @classmethod
    def _validate_nonempty_text(cls, value: str) -> str:
        """Reject empty or whitespace-only text fields."""
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value
