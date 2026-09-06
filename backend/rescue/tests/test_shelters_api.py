"""API tests for the rescue shelter endpoint."""

from fastapi.testclient import TestClient

from backend.rescue.api import shelters
from backend.rescue.main import app

client = TestClient(app)


def test_nearest_shelter_returns_shelter_data() -> None:
    response = client.get(
        "/nearest-shelter", params={"latitude": 40.7128, "longitude": -74.0060}
    )

    assert response.status_code == 200
    assert response.json() == {
        "shelter_id": "shelter-nyc-01",
        "name": "Lower Manhattan Community Shelter",
        "latitude": 40.7128,
        "longitude": -74.006,
        "capacity": 300,
        "occupied": 180,
        "emergency_available": True,
    }


def test_nearest_shelter_response_has_correct_structure() -> None:
    response = client.get(
        "/nearest-shelter", params={"latitude": 40.7128, "longitude": -74.0060}
    )

    assert response.status_code == 200
    assert set(response.json()) == {
        "shelter_id",
        "name",
        "latitude",
        "longitude",
        "capacity",
        "occupied",
        "emergency_available",
    }


def test_invalid_latitude_returns_422() -> None:
    response = client.get(
        "/nearest-shelter", params={"latitude": 90.1, "longitude": -74.0060}
    )

    assert response.status_code == 422


def test_invalid_longitude_returns_422() -> None:
    response = client.get(
        "/nearest-shelter", params={"latitude": 40.7128, "longitude": -180.1}
    )

    assert response.status_code == 422


def test_no_suitable_shelter_returns_400(monkeypatch) -> None:
    def raise_no_suitable_shelter(latitude: float, longitude: float):
        raise ValueError("no suitable shelter available")

    monkeypatch.setattr(shelters, "get_nearest_shelter", raise_no_suitable_shelter)

    response = client.get(
        "/nearest-shelter", params={"latitude": 40.7128, "longitude": -74.0060}
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "no suitable shelter available"}