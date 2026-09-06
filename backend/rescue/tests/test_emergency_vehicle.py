"""Unit tests for the `EmergencyVehicle` Pydantic model."""

from pydantic import ValidationError
import pytest

from backend.rescue.models.emergency_vehicle import (
    EmergencyVehicle,
    VehicleStatus,
    VehicleType,
)


def _base_kwargs() -> dict:
    return {
        "vehicle_id": "vehicle-101",
        "registration_number": "GG-EM-101",
        "vehicle_type": VehicleType.AMBULANCE,
        "latitude": 40.0,
        "longitude": -70.0,
        "status": VehicleStatus.AVAILABLE,
        "capacity": 4,
    }


def test_valid_emergency_vehicle_can_be_created() -> None:
    vehicle = EmergencyVehicle(**_base_kwargs())
    assert vehicle.vehicle_id == "vehicle-101"
    assert vehicle.registration_number == "GG-EM-101"


@pytest.mark.parametrize("vehicle_type", list(VehicleType))
def test_each_vehicle_type_works(vehicle_type: VehicleType) -> None:
    data = _base_kwargs()
    data["vehicle_type"] = vehicle_type
    vehicle = EmergencyVehicle(**data)
    assert vehicle.vehicle_type == vehicle_type


@pytest.mark.parametrize("status", list(VehicleStatus))
def test_each_vehicle_status_works(status: VehicleStatus) -> None:
    data = _base_kwargs()
    data["status"] = status
    vehicle = EmergencyVehicle(**data)
    assert vehicle.status == status


@pytest.mark.parametrize("latitude", [90.1, -90.1, 100.0])
def test_invalid_latitude_is_rejected(latitude: float) -> None:
    data = _base_kwargs()
    data["latitude"] = latitude
    with pytest.raises(ValidationError):
        EmergencyVehicle(**data)


@pytest.mark.parametrize("longitude", [180.1, -180.1, 200.0])
def test_invalid_longitude_is_rejected(longitude: float) -> None:
    data = _base_kwargs()
    data["longitude"] = longitude
    with pytest.raises(ValidationError):
        EmergencyVehicle(**data)


def test_negative_capacity_is_rejected() -> None:
    data = _base_kwargs()
    data["capacity"] = -1
    with pytest.raises(ValidationError):
        EmergencyVehicle(**data)


def test_assigned_mission_id_is_optional() -> None:
    vehicle = EmergencyVehicle(**_base_kwargs())
    assert vehicle.assigned_mission_id is None


def test_assigned_mission_id_is_stored_when_provided() -> None:
    data = _base_kwargs()
    data["assigned_mission_id"] = "mission-42"
    vehicle = EmergencyVehicle(**data)
    assert vehicle.assigned_mission_id == "mission-42"