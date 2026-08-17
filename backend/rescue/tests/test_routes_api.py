"""API tests for the route calculation endpoint."""

import pytest
from fastapi.testclient import TestClient

from backend.rescue.main import app

client = TestClient(app)


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "origin_latitude": 0.0,
        "origin_longitude": 0.0,
        "destination_latitude": 0.0,
        "destination_longitude": 1.0,
        "disaster_id": "disaster-001",
    }
    payload.update(overrides)
    return payload


def test_valid_route_request_returns_http_200() -> None:
    response = client.post("/calculate-route", json=_valid_payload())

    assert response.status_code == 200


def test_valid_route_response_contains_expected_fields() -> None:
    response = client.post("/calculate-route", json=_valid_payload())
    data = response.json()

    assert set(data.keys()) >= {
        "distance_km",
        "estimated_duration_minutes",
        "route_risk_score",
        "route_status",
        "explanation",
    }


def test_valid_request_with_disaster_id_is_accepted() -> None:
    response = client.post("/calculate-route", json=_valid_payload(disaster_id="incident-42"))

    assert response.status_code == 200


def test_request_without_disaster_id_is_accepted() -> None:
    payload = _valid_payload()
    payload.pop("disaster_id")

    response = client.post("/calculate-route", json=payload)

    assert response.status_code == 200


def test_invalid_origin_latitude_greater_than_90_returns_422() -> None:
    response = client.post("/calculate-route", json=_valid_payload(origin_latitude=90.1))

    assert response.status_code == 422


def test_invalid_origin_latitude_less_than_negative_90_returns_422() -> None:
    response = client.post("/calculate-route", json=_valid_payload(origin_latitude=-90.1))

    assert response.status_code == 422


def test_invalid_origin_longitude_greater_than_180_returns_422() -> None:
    response = client.post("/calculate-route", json=_valid_payload(origin_longitude=180.1))

    assert response.status_code == 422


def test_invalid_origin_longitude_less_than_negative_180_returns_422() -> None:
    response = client.post("/calculate-route", json=_valid_payload(origin_longitude=-180.1))

    assert response.status_code == 422


def test_invalid_destination_latitude_returns_422() -> None:
    response = client.post("/calculate-route", json=_valid_payload(destination_latitude=90.1))

    assert response.status_code == 422


def test_invalid_destination_longitude_returns_422() -> None:
    response = client.post("/calculate-route", json=_valid_payload(destination_longitude=180.1))

    assert response.status_code == 422


def test_missing_origin_latitude_returns_422() -> None:
    payload = _valid_payload()
    payload.pop("origin_latitude")

    response = client.post("/calculate-route", json=payload)

    assert response.status_code == 422


def test_missing_origin_longitude_returns_422() -> None:
    payload = _valid_payload()
    payload.pop("origin_longitude")

    response = client.post("/calculate-route", json=payload)

    assert response.status_code == 422


def test_missing_destination_latitude_returns_422() -> None:
    payload = _valid_payload()
    payload.pop("destination_latitude")

    response = client.post("/calculate-route", json=payload)

    assert response.status_code == 422


def test_missing_destination_longitude_returns_422() -> None:
    payload = _valid_payload()
    payload.pop("destination_longitude")

    response = client.post("/calculate-route", json=payload)

    assert response.status_code == 422


def test_blank_disaster_id_returns_422() -> None:
    response = client.post("/calculate-route", json=_valid_payload(disaster_id="   "))

    assert response.status_code == 422


def test_returned_route_status_is_either_ok_or_caution() -> None:
    response = client.post("/calculate-route", json=_valid_payload())
    status = response.json()["route_status"]

    assert status in {"OK", "CAUTION"}


def test_returned_distance_km_is_non_negative() -> None:
    response = client.post("/calculate-route", json=_valid_payload())

    assert response.json()["distance_km"] >= 0


def test_returned_estimated_duration_minutes_is_non_negative() -> None:
    response = client.post("/calculate-route", json=_valid_payload())

    assert response.json()["estimated_duration_minutes"] >= 0


def test_returned_route_risk_score_is_between_zero_and_one() -> None:
    response = client.post("/calculate-route", json=_valid_payload())
    score = response.json()["route_risk_score"]

    assert 0 <= score <= 1


def test_repeating_the_same_request_produces_the_same_response() -> None:
    payload = _valid_payload()

    first = client.post("/calculate-route", json=payload)
    second = client.post("/calculate-route", json=payload)

    assert first.json() == second.json()
