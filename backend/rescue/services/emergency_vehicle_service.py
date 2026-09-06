"""Emergency vehicle service for the Resource & Rescue Management module.

Provides deterministic in-memory vehicle data and lookup helpers for
available emergency vehicles.
"""

from __future__ import annotations

from backend.rescue.models.emergency_vehicle import (
    EmergencyVehicle,
    VehicleStatus,
    VehicleType,
)
from backend.rescue.utils.geo import haversine_km


# Deterministic, realistic mock emergency vehicles for local testing.
# The list order is used as a stable tie-breaker when distances match.
_VEHICLES: list[EmergencyVehicle] = [
    EmergencyVehicle(
        vehicle_id="ambulance-ny-01",
        registration_number="NY-EMS-101",
        vehicle_type=VehicleType.AMBULANCE,
        latitude=40.7128,
        longitude=-74.0060,
        status=VehicleStatus.AVAILABLE,
        capacity=4,
    ),
    EmergencyVehicle(
        vehicle_id="firetruck-la-01",
        registration_number="LA-FD-202",
        vehicle_type=VehicleType.FIRE_TRUCK,
        latitude=34.0522,
        longitude=-118.2437,
        status=VehicleStatus.AVAILABLE,
        capacity=6,
    ),
    EmergencyVehicle(
        vehicle_id="rescue-chi-01",
        registration_number="CHI-RS-303",
        vehicle_type=VehicleType.RESCUE_VEHICLE,
        latitude=41.8781,
        longitude=-87.6298,
        status=VehicleStatus.AVAILABLE,
        capacity=8,
    ),
    EmergencyVehicle(
        vehicle_id="supply-hou-01",
        registration_number="HOU-SUP-404",
        vehicle_type=VehicleType.SUPPLY_TRUCK,
        latitude=29.7604,
        longitude=-95.3698,
        status=VehicleStatus.AVAILABLE,
        capacity=120,
    ),
    EmergencyVehicle(
        vehicle_id="ambulance-mia-02",
        registration_number="MIA-EMS-505",
        vehicle_type=VehicleType.AMBULANCE,
        latitude=25.7617,
        longitude=-80.1918,
        status=VehicleStatus.IN_TRANSIT,
        capacity=4,
        assigned_mission_id="mission-2001",
    ),
    EmergencyVehicle(
        vehicle_id="rescue-den-02",
        registration_number="DEN-RS-606",
        vehicle_type=VehicleType.RESCUE_VEHICLE,
        latitude=39.7392,
        longitude=-104.9903,
        status=VehicleStatus.MAINTENANCE,
        capacity=10,
    ),
]


def get_available_vehicles(
    vehicle_type: VehicleType | None = None,
) -> list[EmergencyVehicle]:
    """Return available vehicles, optionally filtered by vehicle type.

    Only vehicles whose status is ``AVAILABLE`` are returned. The original
    in-memory order is preserved for deterministic results.
    """
    return [
        vehicle
        for vehicle in _VEHICLES
        if vehicle.status == VehicleStatus.AVAILABLE
        and (vehicle_type is None or vehicle.vehicle_type == vehicle_type)
    ]


def get_nearest_available_vehicle(
    latitude: float,
    longitude: float,
    vehicle_type: VehicleType | None = None,
) -> EmergencyVehicle:
    """Return the nearest available vehicle to the supplied coordinates.

    Args:
        latitude: Query latitude in decimal degrees.
        longitude: Query longitude in decimal degrees.
        vehicle_type: Optional vehicle type filter.

    Raises:
        ValueError: If coordinates are outside valid geographic bounds or no
            available vehicle matches the optional type filter.
    """
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError("latitude must be between -90 and 90")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError("longitude must be between -180 and 180")

    available_vehicles = get_available_vehicles(vehicle_type)
    if not available_vehicles:
        raise ValueError("no suitable vehicle available")

    return min(
        available_vehicles,
        key=lambda vehicle: haversine_km(
            latitude, longitude, vehicle.latitude, vehicle.longitude
        ),
    )