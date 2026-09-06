from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.rescue.models.emergency_vehicle import (
    EmergencyVehicle,
    VehicleType,
)
from backend.rescue.services import emergency_vehicle_service

router = APIRouter()


@router.get(
    "/available-vehicle",
    response_model=EmergencyVehicle,
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
    return vehicles[0]


@router.get(
    "/nearest-vehicle",
    response_model=EmergencyVehicle,
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
        return emergency_vehicle_service.get_nearest_available_vehicle(
            latitude, longitude, vehicle_type
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc