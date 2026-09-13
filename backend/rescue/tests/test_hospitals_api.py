"""API tests for the rescue hospital endpoints."""

from fastapi.testclient import TestClient

from backend.rescue.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "resource-management",
    }


def test_nearest_hospital_returns_hospital_data() -> None:
    response = client.get("/nearest-hospital", params={"latitude": 12.9716, "longitude": 77.5946})
    assert response.status_code == 200

    data = response.json()
    assert data["hospital_id"] == "blr-central-test"
    assert data["name"] == "Bengaluru Central Care Hospital (Mock)"
    assert data["latitude"] == 12.9716
    assert data["longitude"] == 77.5946
    assert data["bed_capacity"] == 500
    assert data["available_beds"] == 120
    assert data["icu_capacity"] == 50
    assert data["available_icu"] == 12
    assert data["emergency_available"] is True


def test_invalid_latitude_returns_422() -> None:
    response = client.get("/nearest-hospital", params={"latitude": 90.1, "longitude": -74.0060})
    assert response.status_code == 422


def test_invalid_longitude_returns_422() -> None:
    response = client.get("/nearest-hospital", params={"latitude": 40.7128, "longitude": -180.1})
    assert response.status_code == 422


def test_missing_latitude_returns_422() -> None:
    response = client.get("/nearest-hospital", params={"longitude": -74.0060})
    assert response.status_code == 422


def test_missing_longitude_returns_422() -> None:
    response = client.get("/nearest-hospital", params={"latitude": 40.7128})
    assert response.status_code == 422
