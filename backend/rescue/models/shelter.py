"""Pydantic models for the rescue module: shelter definitions."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ShelterStatus(str, Enum):
    """Operational state of an emergency shelter."""

    ACCEPTING_EVACUEES = "ACCEPTING_EVACUEES"
    AVAILABLE = "AVAILABLE"
    FULL = "FULL"
    CLOSED = "CLOSED"


class EmergencyShelter(BaseModel):
    """Represents a shelter used for emergency evacuation management."""

    shelter_id: str = Field(..., min_length=1, description="Unique shelter identifier")
    name: str = Field(..., min_length=1, description="Human-readable shelter name")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    capacity: int = Field(..., ge=0)
    available_capacity: int = Field(..., ge=0)
    status: ShelterStatus

    @model_validator(mode="after")
    def _check_capacity(self) -> EmergencyShelter:
        if self.available_capacity > self.capacity:
            raise ValueError("available_capacity must not exceed capacity")
        return self


class Shelter(BaseModel):
    """Represents an emergency shelter with capacity information."""

    shelter_id: str = Field(..., description="Unique shelter identifier")
    name: str = Field(..., description="Human-readable shelter name")

    latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Latitude in decimal degrees (-90 to 90)"
    )
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude in decimal degrees (-180 to 180)"
    )

    capacity: int = Field(..., ge=0, description="Total shelter capacity (>= 0)")
    occupied: int = Field(..., ge=0, description="Currently occupied spaces (>= 0)")
    emergency_available: bool = Field(
        ..., description="Whether the shelter is available for emergencies"
    )

    @model_validator(mode="after")
    def _check_occupancy(self) -> Shelter:
        """Ensure occupied spaces do not exceed shelter capacity."""
        if self.occupied > self.capacity:
            raise ValueError("occupied must not exceed capacity")
        return self

    @property
    def available_spaces(self) -> int:
        """Return the number of unoccupied shelter spaces."""
        return self.capacity - self.occupied