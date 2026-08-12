"""Pydantic models for the rescue module: hospital definitions.

This module defines the `Hospital` model used to represent hospital
capacity and location information for the Resource & Rescue Management
component. It uses Pydantic v2 `BaseModel` with field constraints and
an after-model validator to enforce cross-field invariants.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class Hospital(BaseModel):
    """Represents a hospital with capacity and availability information.

    Focused solely on hospital data used by resource-management logic.
    """

    hospital_id: str = Field(..., description="Unique hospital identifier")
    name: str = Field(..., description="Human-readable hospital name")

    latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Latitude in decimal degrees (-90 to 90)"
    )
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude in decimal degrees (-180 to 180)"
    )

    bed_capacity: int = Field(..., ge=0, description="Total number of beds (>= 0)")
    available_beds: int = Field(
        ..., ge=0, description="Currently available non-ICU beds (>= 0)"
    )

    icu_capacity: int = Field(..., ge=0, description="Total number of ICU beds (>= 0)")
    available_icu: int = Field(..., ge=0, description="Currently available ICU beds (>= 0)")

    emergency_available: bool = Field(
        ..., description="Whether the emergency department is accepting patients"
    )

    @model_validator(mode="after")
    def _check_availability(self) -> Hospital:
        """Ensure availability values do not exceed their capacities."""
        if self.available_beds > self.bed_capacity:
            raise ValueError("available_beds must not exceed bed_capacity")
        if self.available_icu > self.icu_capacity:
            raise ValueError("available_icu must not exceed icu_capacity")
        return self
