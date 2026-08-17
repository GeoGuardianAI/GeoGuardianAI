"""API tests for the rescue team endpoints."""

from fastapi.testclient import TestClient

from backend.rescue.main import app

client = TestClient(app)


def test_available_team_with_valid_coordinates_returns_http_200() -> None:
    response = client.get("/available-team", params={"latitude": 40.7128, "longitude": -74.0060})
    assert response.status_code == 200


def test_response_is_a_list() -> None:
    response = client.get("/available-team", params={"latitude": 40.7128, "longitude": -74.0060})
    assert isinstance(response.json(), list)


def test_returned_objects_contain_expected_rescue_team_fields() -> None:
    response = client.get("/available-team", params={"latitude": 40.7128, "longitude": -74.0060})
    data = response.json()

    assert data
    first = data[0]
    assert set(first.keys()) >= {
        "team_id",
        "name",
        "team_type",
        "latitude",
        "longitude",
        "members",
        "specialization",
        "availability",
        "current_mission_id",
    }
    assert first["team_id"] == "rescue-ny-01"
    assert first["name"] == "New York Mountain Rescue"
    assert first["availability"] == "AVAILABLE"


def test_specialization_filtering_works() -> None:
    response = client.get(
        "/available-team",
        params={"latitude": 40.7128, "longitude": -74.0060, "specialization": "search"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data
    assert all("search" in [item.lower() for item in team["specialization"]] for team in data)


def test_invalid_latitude_returns_422() -> None:
    response = client.get("/available-team", params={"latitude": 90.1, "longitude": -74.0060})
    assert response.status_code == 422


def test_invalid_longitude_returns_422() -> None:
    response = client.get("/available-team", params={"latitude": 40.7128, "longitude": -180.1})
    assert response.status_code == 422


def test_missing_latitude_returns_422() -> None:
    response = client.get("/available-team", params={"longitude": -74.0060})
    assert response.status_code == 422


def test_missing_longitude_returns_422() -> None:
    response = client.get("/available-team", params={"latitude": 40.7128})
    assert response.status_code == 422


def test_no_matching_specialization_returns_empty_list() -> None:
    response = client.get(
        "/available-team",
        params={"latitude": 40.7128, "longitude": -74.0060, "specialization": "nonexistent"},
    )
    assert response.status_code == 200
    assert response.json() == []
