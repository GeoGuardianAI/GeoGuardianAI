"""Pydantic models for deterministic disaster risk prioritization."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class PriorityLevel(str, Enum):
    """Priority category derived from a normalized risk score."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskPriorityRequest(BaseModel):
    """Validated information used to calculate a disaster risk priority."""

    disaster_id: str = Field(..., description="Unique disaster identifier")
    disaster_type: str = Field(..., description="Type or category of disaster")
    latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Latitude in decimal degrees (-90 to 90)"
    )
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude in decimal degrees (-180 to 180)"
    )
    severity: int = Field(..., ge=1, le=5, description="Disaster severity on a 1-5 scale")
    affected_population: int = Field(
        ..., ge=0, description="Number of people affected by the disaster (>= 0)"
    )
    critical_infrastructure: bool = Field(
        default=False,
        description="Whether critical infrastructure is affected",
    )

    @field_validator("disaster_id", "disaster_type")
    @classmethod
    def _validate_nonempty_text(cls, value: str) -> str:
        """Reject empty or whitespace-only disaster text."""
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value


class RiskPriorityResult(BaseModel):
    """Represents the calculated risk score, priority, and explanation."""

    disaster_id: str = Field(..., description="Identifier of the assessed disaster")
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Risk score from 0 to 100")
    priority_level: PriorityLevel = Field(
        ..., description="Priority category derived from the risk score"
    )
    reasoning: str = Field(..., min_length=1, description="Explanation of the risk calculation")

    @field_validator("disaster_id", "reasoning")
    @classmethod
    def _validate_nonempty_text(cls, value: str) -> str:
        """Reject empty or whitespace-only result text."""
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value