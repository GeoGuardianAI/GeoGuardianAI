"""Pydantic models for emergency route-planning requests and responses.

These models are intentionally data-only and do not include routing logic or
external API calls. They define validated request and response payloads for
route estimation and risk evaluation.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class RouteStatus(str, Enum):
    """Operational status for a route assessment in the rescue domain."""

    OK = "OK"
    CAUTION = "CAUTION"


class RouteRequest(BaseModel):
    """Represents a route-planning request between two geographic points."""

    origin_latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Origin latitude in decimal degrees (-90 to 90)"
    )
    origin_longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Origin longitude in decimal degrees (-180 to 180)"
    )
    destination_latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Destination latitude in decimal degrees (-90 to 90)"
    )
    destination_longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Destination longitude in decimal degrees (-180 to 180)"
    )
    disaster_id: str | None = Field(
        default=None,
        description="Optional identifier for the disaster event associated with the route",
    )

    @field_validator("disaster_id")
    @classmethod
    def validate_disaster_id(cls, value: str | None) -> str | None:
        """Reject blank or whitespace-only disaster IDs."""
        if value is not None and not value.strip():
            raise ValueError("disaster_id must not be blank")
        return value


class RouteResponse(BaseModel):
    """Represents a route estimate and risk summary for a trip."""

    distance_km: float = Field(
        ..., ge=0.0, description="Estimated route distance in kilometers"
    )
    estimated_duration_minutes: float = Field(
        ..., ge=0.0, description="Estimated trip duration in minutes"
    )
    route_risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Risk score for the route, normalized from 0 to 1"
    )
    route_status: RouteStatus = Field(
        ..., description="Status of the route assessment"
    )
    explanation: str = Field(
        ..., description="Human-readable explanation of the route estimate"
    )

    @field_validator("explanation")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        """Reject blank or whitespace-only explanations."""
        if not value or not value.strip():
            raise ValueError("explanation must not be blank")
        return value

