"""API tests for the resource allocation endpoint."""

from fastapi.testclient import TestClient

from backend.rescue.main import app

client = TestClient(app)


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "disaster_id": "disaster-001",
        "disaster_type": "flood",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "severity": 3,
        "required_specialization": "mountain rescue",
    }
    payload.update(overrides)
    return payload


def test_valid_allocation_request_returns_http_200() -> None:
    response = client.post(
        "/allocate-resource",
        json=_valid_payload(),
    )

    assert response.status_code == 200
    data = response.json()

    assert data["disaster_id"] == "disaster-001"
    assert data["recommended_hospital"] is not None
    assert data["recommended_rescue_team"] is not None
    assert data["recommended_rescue_team"]["team_id"] == "rescue-ny-01"
    assert data["recommended_rescue_team"]["availability"] == "AVAILABLE"
    assert 0 <= data["priority_score"] <= 100
    assert data["estimated_distance_km"] >= 0
    assert data["reasoning"].strip() != ""


def test_nonexistent_specialization_returns_http_404() -> None:
    response = client.post(
        "/allocate-resource",
        json=_valid_payload(required_specialization="xyz_nonexistent"),
    )

    assert response.status_code == 404
    detail = response.json().get("detail")
    assert isinstance(detail, dict)
    assert "No suitable rescue team" in detail["error"]


def test_unavailable_team_is_not_selected() -> None:
    response = client.post(
        "/allocate-resource",
        json={
            "disaster_id": "disaster-houston-001",
            "disaster_type": "flood",
            "latitude": 29.7604,
            "longitude": -95.3698,
            "severity": 4,
            "required_specialization": "flood rescue",
        },
    )

    assert response.status_code == 404
    detail = response.json().get("detail")
    assert isinstance(detail, dict)
    assert "No suitable rescue team" in detail["error"]


def test_invalid_latitude_returns_http_422() -> None:
    response = client.post(
        "/allocate-resource",
        json=_valid_payload(latitude=90.1),
    )

    assert response.status_code == 422


def test_invalid_longitude_returns_http_422() -> None:
    response = client.post(
        "/allocate-resource",
        json=_valid_payload(longitude=180.1),
    )

    assert response.status_code == 422


def test_invalid_severity_returns_http_422() -> None:
    response = client.post(
        "/allocate-resource",
        json=_valid_payload(severity=0),
    )

    assert response.status_code == 422


def test_missing_disaster_id_returns_http_422() -> None:
    payload = _valid_payload()
    payload.pop("disaster_id")

    response = client.post("/allocate-resource", json=payload)

    assert response.status_code == 422


def test_missing_disaster_type_returns_http_422() -> None:
    payload = _valid_payload()
    payload.pop("disaster_type")

    response = client.post("/allocate-resource", json=payload)

    assert response.status_code == 422


def test_missing_latitude_returns_http_422() -> None:
    payload = _valid_payload()
    payload.pop("latitude")

    response = client.post("/allocate-resource", json=payload)

    assert response.status_code == 422


def test_missing_longitude_returns_http_422() -> None:
    payload = _valid_payload()
    payload.pop("longitude")

    response = client.post("/allocate-resource", json=payload)

    assert response.status_code == 422
