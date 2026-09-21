"""Focused tests for emergency vehicle tracking endpoints."""

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from backend.rescue.main import app
from backend.rescue.models.emergency_vehicle import EmergencyVehicle, VehicleStatus
from backend.rescue.services import emergency_vehicle_service


client = TestClient(app)


@pytest.fixture(autouse=True)
def restore_vehicle_registry():
    original = [vehicle.model_copy(deep=True) for vehicle in emergency_vehicle_service._VEHICLES]
    yield
    emergency_vehicle_service._VEHICLES = original


def test_vehicle_model_requires_valid_id_and_status() -> None:
    with pytest.raises(ValidationError):
        EmergencyVehicle(vehicle_id="", latitude=12.9, longitude=77.6, status="AVAILABLE")

    with pytest.raises(ValidationError):
        EmergencyVehicle(vehicle_id="vehicle-1", latitude=12.9, longitude=77.6, status="INVALID")


def test_get_vehicles_returns_all_vehicle_fields() -> None:
    response = client.get("/vehicles")

    assert response.status_code == 200
    assert len(response.json()) == len(emergency_vehicle_service._VEHICLES)
    assert set(response.json()[0]) >= {
        "vehicle_id",
        "name",
        "vehicle_type",
        "latitude",
        "longitude",
        "status",
        "current_mission_id",
    }


def test_get_available_vehicles_returns_only_available_vehicles() -> None:
    response = client.get("/available-vehicles")

    assert response.status_code == 200
    assert response.json()
    assert all(vehicle["status"] == "AVAILABLE" for vehicle in response.json())


def test_location_update_changes_vehicle_coordinates() -> None:
    response = client.post(
        "/vehicles/ambulance-blr-01/location",
        json={"latitude": 12.9352, "longitude": 77.6245},
    )

    assert response.status_code == 200
    assert response.json()["latitude"] == 12.9352
    assert response.json()["longitude"] == 77.6245


def test_location_update_rejects_invalid_coordinates() -> None:
    response = client.post(
        "/vehicles/ambulance-blr-01/location",
        json={"latitude": 91, "longitude": 77.6245},
    )

    assert response.status_code == 422


def test_status_update_changes_vehicle_status() -> None:
    response = client.post(
        "/vehicles/ambulance-blr-01/status",
        json={"status": "IN_TRANSIT"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "IN_TRANSIT"


def test_status_update_rejects_invalid_status() -> None:
    response = client.post(
        "/vehicles/ambulance-blr-01/status",
        json={"status": "FLYING"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("path", [
    "/vehicles/missing-vehicle/location",
    "/vehicles/missing-vehicle/status",
])
def test_updates_return_404_for_unknown_vehicle(path: str) -> None:
    payload = {"latitude": 12.9, "longitude": 77.6} if path.endswith("location") else {"status": VehicleStatus.AVAILABLE.value}

    response = client.post(path, json=payload)

    assert response.status_code == 404
