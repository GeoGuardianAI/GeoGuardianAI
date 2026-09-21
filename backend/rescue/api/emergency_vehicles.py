from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from backend.rescue.models.emergency_vehicle import (
    EmergencyVehicle,
    VehicleStatus,
    VehicleType,
)
from backend.rescue.services import emergency_vehicle_service

router = APIRouter()


class LegacyEmergencyVehicle(BaseModel):
    """Response shape retained for the existing singular vehicle endpoints."""

    vehicle_id: str
    registration_number: str
    vehicle_type: VehicleType
    latitude: float
    longitude: float
    status: str
    capacity: int
    assigned_mission_id: str | None = None


class VehicleLocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class VehicleStatusUpdate(BaseModel):
    status: VehicleStatus


def _legacy_vehicle(vehicle):
    return LegacyEmergencyVehicle(
        vehicle_id=vehicle.vehicle_id,
        registration_number=vehicle.registration_number,
        vehicle_type=vehicle.vehicle_type,
        latitude=vehicle.latitude,
        longitude=vehicle.longitude,
        status=vehicle.status.value,
        capacity=vehicle.capacity,
        assigned_mission_id=vehicle.assigned_mission_id,
    )


@router.get("/vehicles", response_model=list[EmergencyVehicle])
def vehicles() -> list[EmergencyVehicle]:
    """Return all registered emergency vehicles."""
    return emergency_vehicle_service.get_vehicles()


@router.get("/available-vehicles", response_model=list[EmergencyVehicle])
def available_vehicles() -> list[EmergencyVehicle]:
    """Return vehicles currently available for assignment."""
    return emergency_vehicle_service.get_available_vehicles()


@router.post("/vehicles/{vehicle_id}/location", response_model=EmergencyVehicle)
def update_vehicle_location(vehicle_id: str, update: VehicleLocationUpdate) -> EmergencyVehicle:
    """Update a registered vehicle's location."""
    try:
        return emergency_vehicle_service.update_vehicle_location(
            vehicle_id, update.latitude, update.longitude
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/vehicles/{vehicle_id}/status", response_model=EmergencyVehicle)
def update_vehicle_status(vehicle_id: str, update: VehicleStatusUpdate) -> EmergencyVehicle:
    """Update a registered vehicle's operational status."""
    try:
        return emergency_vehicle_service.update_vehicle_status(vehicle_id, update.status)
    except ValueError as exc:
        if "does not exist" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/available-vehicle",
    response_model=LegacyEmergencyVehicle,
    summary="Find an available emergency vehicle",
    description=(
        "Return an available emergency vehicle, optionally filtered by vehicle type."
    ),
)
def available_vehicle(
    vehicle_type: VehicleType | None = Query(
        default=None,
        description="Optional vehicle type filter",
    ),
) -> EmergencyVehicle:
    """Return the first available vehicle from the deterministic service collection."""
    vehicles = emergency_vehicle_service.get_available_vehicles(vehicle_type)
    if not vehicles:
        raise HTTPException(status_code=400, detail="no suitable vehicle available")
    return _legacy_vehicle(vehicles[0])


@router.get(
    "/nearest-vehicle",
    response_model=LegacyEmergencyVehicle,
    summary="Find the nearest available emergency vehicle",
    description=(
        "Return the nearest available emergency vehicle to the provided latitude "
        "and longitude, optionally filtered by vehicle type."
    ),
)
def nearest_vehicle(
    latitude: float = Query(
        ..., ge=-90.0, le=90.0, description="Latitude in decimal degrees between -90 and 90"
    ),
    longitude: float = Query(
        ..., ge=-180.0, le=180.0, description="Longitude in decimal degrees between -180 and 180"
    ),
    vehicle_type: VehicleType | None = Query(
        default=None,
        description="Optional vehicle type filter",
    ),
) -> EmergencyVehicle:
    """Return the nearest available vehicle for the requested coordinates."""
    try:
        return _legacy_vehicle(emergency_vehicle_service.get_nearest_available_vehicle(
            latitude, longitude, vehicle_type
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc