"""Unit tests for the emergency vehicle service."""

import pytest

from backend.rescue.models.emergency_vehicle import VehicleStatus, VehicleType
from backend.rescue.services import emergency_vehicle_service


def test_available_vehicles_are_returned() -> None:
    vehicles = emergency_vehicle_service.get_available_vehicles()

    assert vehicles
    assert all(vehicle.status == VehicleStatus.AVAILABLE for vehicle in vehicles)


def test_nearest_available_vehicle_is_returned() -> None:
    vehicle = emergency_vehicle_service.get_nearest_available_vehicle(40.7128, -74.0060)

    assert vehicle.vehicle_id == "ambulance-ny-01"


def test_unavailable_vehicles_are_ignored() -> None:
    vehicles = emergency_vehicle_service.get_available_vehicles()

    unavailable_ids = {"ambulance-mia-02", "rescue-den-02"}
    assert all(vehicle.vehicle_id not in unavailable_ids for vehicle in vehicles)


@pytest.mark.parametrize("vehicle_type", list(VehicleType))
def test_vehicle_type_filtering_works(vehicle_type: VehicleType) -> None:
    vehicles = emergency_vehicle_service.get_available_vehicles(vehicle_type)

    assert vehicles
    assert all(vehicle.vehicle_type == vehicle_type for vehicle in vehicles)


@pytest.mark.parametrize("latitude", [-90.1, 90.1])
def test_invalid_latitude_raises_value_error(latitude: float) -> None:
    with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
        emergency_vehicle_service.get_nearest_available_vehicle(latitude, -74.0060)


@pytest.mark.parametrize("longitude", [-180.1, 180.1])
def test_invalid_longitude_raises_value_error(longitude: float) -> None:
    with pytest.raises(ValueError, match="longitude must be between -180 and 180"):
        emergency_vehicle_service.get_nearest_available_vehicle(40.7128, longitude)


def test_no_suitable_vehicle_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(emergency_vehicle_service, "_VEHICLES", [])
    with pytest.raises(ValueError, match="no suitable vehicle available"):
        emergency_vehicle_service.get_nearest_available_vehicle(40.7128, -74.0060)


def test_vehicle_results_are_deterministic() -> None:
    first = emergency_vehicle_service.get_available_vehicles()
    second = emergency_vehicle_service.get_available_vehicles()

    assert [vehicle.vehicle_id for vehicle in first] == [
        vehicle.vehicle_id for vehicle in second
    ]