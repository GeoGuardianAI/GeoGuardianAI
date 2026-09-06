"""API tests for the risk-priority endpoint."""

import pytest
from fastapi.testclient import TestClient

from backend.rescue.main import app

client = TestClient(app)


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "disaster_id": "disaster-api-001",
        "disaster_type": "flood",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "severity": 1,
        "affected_population": 0,
        "critical_infrastructure": False,
    }
    payload.update(overrides)
    return payload


def test_valid_low_risk_request_returns_http_200() -> None:
    response = client.post("/risk-priority", json=_valid_payload())

    assert response.status_code == 200
    assert response.json()["priority_level"] == "LOW"
    assert response.json()["risk_score"] == 0.0


def test_valid_critical_risk_request_returns_http_200() -> None:
    response = client.post(
        "/risk-priority",
        json=_valid_payload(
            severity=5,
            affected_population=10000,
            critical_infrastructure=True,
        ),
    )

    assert response.status_code == 200
    assert response.json()["priority_level"] == "CRITICAL"
    assert response.json()["risk_score"] == 100.0


@pytest.mark.parametrize(
    "payload, expected_level",
    [
        (_valid_payload(severity=3, affected_population=3333), "MEDIUM"),
        (_valid_payload(severity=4, affected_population=5000), "HIGH"),
    ],
)
def test_medium_and_high_priority_responses(
    payload: dict[str, object], expected_level: str
) -> None:
    response = client.post("/risk-priority", json=payload)

    assert response.status_code == 200
    assert response.json()["priority_level"] == expected_level


def test_response_contains_expected_fields() -> None:
    response = client.post("/risk-priority", json=_valid_payload())

    assert response.status_code == 200
    assert set(response.json()) == {
        "disaster_id",
        "risk_score",
        "priority_level",
        "reasoning",
    }


def test_invalid_severity_returns_422() -> None:
    response = client.post("/risk-priority", json=_valid_payload(severity=6))

    assert response.status_code == 422


@pytest.mark.parametrize(
    "field, value",
    [("latitude", 90.1), ("longitude", 180.1)],
)
def test_invalid_coordinates_return_422(field: str, value: float) -> None:
    response = client.post("/risk-priority", json=_valid_payload(**{field: value}))

    assert response.status_code == 422


def test_negative_affected_population_returns_422() -> None:
    response = client.post("/risk-priority", json=_valid_payload(affected_population=-1))

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["disaster_id", "disaster_type"])
def test_empty_disaster_text_returns_422(field: str) -> None:
    response = client.post("/risk-priority", json=_valid_payload(**{field: "   "}))

    assert response.status_code == 422