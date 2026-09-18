"""Pydantic models for emergency resource inventory definitions."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ResourceType(str, Enum):
    """Category of an emergency resource held in inventory."""

    FOOD = "FOOD"
    WATER = "WATER"
    MEDICAL_SUPPLIES = "MEDICAL_SUPPLIES"
    RESCUE_EQUIPMENT = "RESCUE_EQUIPMENT"
    TEMPORARY_SHELTER_SUPPLIES = "TEMPORARY_SHELTER_SUPPLIES"


class ResourceAllocationRequest(BaseModel):
    """Represents a request to allocate inventory from a resource."""

    resource_id: str = Field(..., min_length=1, description="Resource identifier")
    quantity: int = Field(..., gt=0, description="Quantity to allocate (> 0)")


class EmergencyResource(BaseModel):
    """Represents an emergency resource and its available inventory quantity."""

    resource_id: str = Field(..., description="Unique emergency resource identifier")
    name: str = Field(..., description="Human-readable resource name")
    resource_type: ResourceType = Field(
        ..., description="Category of the emergency resource"
    )

    total_quantity: int = Field(
        ..., ge=0, description="Total quantity held in inventory (>= 0)"
    )
    available_quantity: int = Field(
        ..., ge=0, description="Quantity currently available for deployment (>= 0)"
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

    @model_validator(mode="after")
    def _check_available_quantity(self) -> EmergencyResource:
        """Ensure available inventory does not exceed total inventory."""
        if self.available_quantity > self.total_quantity:
            raise ValueError("available_quantity must not exceed total_quantity")
        return self