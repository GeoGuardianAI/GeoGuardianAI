"""Pydantic models for disaster resource allocation requests and recommendations.

These models define the validated payload used to describe a disaster event and
represent a recommendation for the best matching hospital and rescue team.
They are intentionally data-only and do not include business logic.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.rescue.models.emergency_resource import EmergencyResource, ResourceType
from backend.rescue.models.hospital import Hospital
from backend.rescue.models.mission import MissionStatus
from backend.rescue.models.rescue_team import RescueTeam


class ResourceAllocationStatus(str, Enum):
    """Lifecycle status for an inventory allocation record."""

    ALLOCATED = "ALLOCATED"
    RELEASED = "RELEASED"
    CANCELLED = "CANCELLED"


class ResourceAllocation(BaseModel):
    """Records inventory allocated to a mission and its disaster."""

    allocation_id: str = Field(..., description="Unique allocation identifier")
    resource_id: str = Field(..., description="Allocated resource identifier")
    quantity: int = Field(..., gt=0, description="Allocated quantity (> 0)")
    mission_id: str = Field(..., description="Mission associated with the allocation")
    disaster_id: str = Field(..., description="Disaster associated with the allocation")
    allocated_at: datetime = Field(..., description="Allocation timestamp")
    status: ResourceAllocationStatus = Field(..., description="Allocation lifecycle status")

    @field_validator("allocation_id", "resource_id", "mission_id", "disaster_id")
    @classmethod
    def _validate_nonempty_text(cls, value: str) -> str:
        """Reject empty or whitespace-only identifiers."""
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value


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
    resource_type: ResourceType | None = Field(
        default=None,
        description="Optional emergency resource type to recommend",
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
    recommended_resources: list[EmergencyResource] = Field(
        default_factory=list,
        description="Available emergency resources ordered by distance",
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


class MissionResourceRecommendationRequest(BaseModel):
    """Request a read-only resource recommendation for an existing mission."""

    mission_id: str = Field(..., min_length=1, description="Existing mission identifier")
    resource_type: ResourceType | None = Field(
        default=None,
        description="Optional strict resource-type filter",
    )
    quantity: int | None = Field(
        default=None,
        gt=0,
        strict=True,
        description="Optional minimum available quantity for each recommendation",
    )

    @field_validator("mission_id")
    @classmethod
    def _validate_mission_id(cls, value: str) -> str:
        """Reject empty or whitespace-only mission identifiers."""
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value


class MissionResourceRecommendation(BaseModel):
    """Read-only resource recommendations scoped to an existing mission."""

    mission_id: str = Field(..., description="Mission associated with the recommendations")
    disaster_id: str = Field(..., description="Disaster associated with the mission")
    destination_latitude: float = Field(..., description="Mission destination latitude")
    destination_longitude: float = Field(..., description="Mission destination longitude")
    resource_type: ResourceType | None = Field(
        ..., description="Strict resource-type filter, if requested"
    )
    requested_quantity: int | None = Field(
        ..., description="Minimum available quantity requested, if provided"
    )
    recommended_resources: list[EmergencyResource] = Field(
        default_factory=list,
        description="Eligible recommendations only; inventory is not allocated",
    )
    recommendation_only: Literal[True] = Field(
        default=True,
        description="Always true; recommendations do not reserve or allocate inventory",
    )
    ranking_order: str = Field(
        default=(
            "strict resource-type filter; available quantity descending; "
            "geographic distance ascending; resource type ascending; resource ID ascending"
        ),
        description="Deterministic ordering applied to eligible resources",
    )


class MissionResourceRequirement(BaseModel):
    """One explicitly requested resource type and quantity."""

    resource_type: ResourceType = Field(..., description="Required emergency resource type")
    quantity: int = Field(..., gt=0, strict=True, description="Required quantity (> 0)")


class MissionResourceReadinessRequest(BaseModel):
    """Explicit resource requirements to assess for an existing mission."""

    mission_id: str = Field(..., min_length=1, description="Existing mission identifier")
    requirements: list[MissionResourceRequirement] = Field(
        ..., min_length=1, description="Explicit resource requirements to assess"
    )

    @field_validator("mission_id")
    @classmethod
    def _validate_readiness_mission_id(cls, value: str) -> str:
        """Reject empty or whitespace-only mission identifiers."""
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("requirements")
    @classmethod
    def _validate_unique_requirement_types(
        cls, value: list[MissionResourceRequirement]
    ) -> list[MissionResourceRequirement]:
        """Prevent duplicate types from double-counting the same inventory."""
        types = [item.resource_type for item in value]
        if len(types) != len(set(types)):
            raise ValueError("requirements must contain each resource type only once")
        return value


class MissionResourceReadinessItem(BaseModel):
    """Readiness details for one requested resource type."""

    resource_type: ResourceType
    requested_quantity: int = Field(..., gt=0)
    inventory_available_quantity: int = Field(..., ge=0)
    mission_allocated_quantity: int = Field(
        ...,
        ge=0,
        description="Quantity in active ALLOCATED records for this mission; not inventory",
    )
    satisfiable: bool
    shortage: int = Field(..., ge=0)


class MissionResourceReadinessResponse(BaseModel):
    """Read-only overall readiness assessment for a mission."""

    mission_id: str
    disaster_id: str
    mission_status: MissionStatus
    ready: bool
    requirements: list[MissionResourceReadinessItem]
    shortages: list[MissionResourceReadinessItem]
    assessment_only: Literal[True] = Field(
        default=True,
        description="Assessment does not allocate resources or change mission state",
    )
