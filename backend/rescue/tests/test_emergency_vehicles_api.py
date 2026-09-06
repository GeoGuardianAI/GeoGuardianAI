"""API tests for the emergency vehicle endpoints."""

from fastapi.testclient import TestClient

from backend.rescue.api import emergency_vehicles
from backend.rescue.main import app

client = TestClient(app)


def test_available_vehicle_returns_vehicle_data() -> None:
    response = client.get("/available-vehicle")

    assert response.status_code == 200
    assert response.json()["vehicle_id"] == "ambulance-ny-01"
    assert response.json()["status"] == "AVAILABLE"


def test_nearest_vehicle_returns_vehicle_data() -> None:
    response = client.get(
        "/nearest-vehicle", params={"latitude": 40.7128, "longitude": -74.0060}
    )

    assert response.status_code == 200
    assert response.json()["vehicle_id"] == "ambulance-ny-01"


def test_vehicle_type_filtering_returns_requested_type() -> None:
    response = client.get("/available-vehicle", params={"vehicle_type": "FIRE_TRUCK"})

    assert response.status_code == 200
    assert response.json()["vehicle_type"] == "FIRE_TRUCK"


def test_invalid_latitude_returns_422() -> None:
    response = client.get(
        "/nearest-vehicle", params={"latitude": 90.1, "longitude": -74.0060}
    )

    assert response.status_code == 422


def test_invalid_longitude_returns_422() -> None:
    response = client.get(
        "/nearest-vehicle", params={"latitude": 40.7128, "longitude": -180.1}
    )

    assert response.status_code == 422


def test_no_available_vehicle_returns_400(monkeypatch) -> None:
    monkeypatch.setattr(
        emergency_vehicles.emergency_vehicle_service,
        "get_available_vehicles",
        lambda vehicle_type=None: [],
    )

    response = client.get("/available-vehicle")

    assert response.status_code == 400
    assert response.json() == {"detail": "no suitable vehicle available"}


def test_available_vehicle_has_correct_response_structure() -> None:
    response = client.get("/available-vehicle")

    assert response.status_code == 200
    assert set(response.json()) == {
        "vehicle_id",
        "registration_number",
        "vehicle_type",
        "latitude",
        "longitude",
        "status",
        "capacity",
        "assigned_mission_id",
    }


def test_nearest_vehicle_returns_correct_http_status_code() -> None:
    response = client.get(
        "/nearest-vehicle", params={"latitude": 40.7128, "longitude": -74.0060}
    )

    assert response.status_code == 200