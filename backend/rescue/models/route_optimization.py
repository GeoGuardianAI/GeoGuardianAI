"""Pydantic models for deterministic route optimization."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class RouteOptimizationRequest(BaseModel):
    """Represents preferences and coordinates for route optimization."""

    origin_latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Origin latitude in decimal degrees (-90 to 90)",
    )
    origin_longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Origin longitude in decimal degrees (-180 to 180)",
    )
    destination_latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Destination latitude in decimal degrees (-90 to 90)",
    )
    destination_longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Destination longitude in decimal degrees (-180 to 180)",
    )
    disaster_id: str | None = Field(
        default=None,
        description="Optional disaster identifier associated with the route",
    )
    risk_tolerance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Maximum preferred route risk from 0 to 1",
    )

    @field_validator("disaster_id")
    @classmethod
    def validate_disaster_id(cls, value: str | None) -> str | None:
        """Reject blank or whitespace-only disaster IDs."""
        if value is not None and not value.strip():
            raise ValueError("disaster_id must not be blank")
        return value


class RouteCandidate(BaseModel):
    """Represents one route option considered by the optimizer."""

    route_id: str = Field(..., description="Unique route candidate identifier")
    distance_km: float = Field(..., ge=0.0, description="Route distance in kilometers")
    estimated_duration_minutes: float = Field(
        ..., ge=0.0, description="Estimated route duration in minutes"
    )
    route_risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Normalized route risk score from 0 to 1"
    )

    @field_validator("route_id")
    @classmethod
    def validate_route_id(cls, value: str) -> str:
        """Reject blank or whitespace-only route IDs."""
        if not value or not value.strip():
            raise ValueError("route_id must not be blank")
        return value


class RouteOptimizationResult(BaseModel):
    """Represents the selected route and its optimization result."""

    selected_route: RouteCandidate = Field(
        ..., description="Selected best route candidate"
    )
    candidates: list[RouteCandidate] = Field(
        ..., min_length=1, description="Route candidates considered by the optimizer"
    )
    optimization_score: float = Field(
        ..., ge=0.0, le=100.0, description="Selected route score from 0 to 100"
    )
    reasoning: str = Field(
        ..., min_length=1, description="Explanation of the route optimization decision"
    )

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning(cls, value: str) -> str:
        """Reject blank or whitespace-only optimization reasoning."""
        if not value.strip():
            raise ValueError("reasoning must not be blank")
        return value