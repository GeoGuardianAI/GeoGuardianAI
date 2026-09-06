"""Pydantic models for emergency vehicle definitions."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class VehicleType(str, Enum):
    """Operational category for an emergency vehicle."""

    AMBULANCE = "AMBULANCE"
    FIRE_TRUCK = "FIRE_TRUCK"
    RESCUE_VEHICLE = "RESCUE_VEHICLE"
    SUPPLY_TRUCK = "SUPPLY_TRUCK"


class VehicleStatus(str, Enum):
    """Current operational status of an emergency vehicle."""

    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    IN_TRANSIT = "IN_TRANSIT"
    MAINTENANCE = "MAINTENANCE"
    UNAVAILABLE = "UNAVAILABLE"


class EmergencyVehicle(BaseModel):
    """Represents an emergency vehicle with location and mission status."""

    vehicle_id: str = Field(..., description="Unique emergency vehicle identifier")
    registration_number: str = Field(
        ..., description="Official vehicle registration number"
    )
    vehicle_type: VehicleType = Field(
        ..., description="Operational category for the vehicle"
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

    status: VehicleStatus = Field(..., description="Current operational status")
    capacity: int = Field(..., ge=0, description="Vehicle capacity (>= 0)")
    assigned_mission_id: str | None = Field(
        default=None,
        description="Identifier for the assigned mission, if any",
    )