"""Focused tests for emergency shelter management."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.rescue.main import app
from backend.rescue.models.shelter import EmergencyShelter, ShelterStatus
from backend.rescue.services import shelter_service


client = TestClient(app)


@pytest.fixture(autouse=True)
def restore_shelter_registry():
    original = [shelter.model_copy(deep=True) for shelter in shelter_service._EMERGENCY_SHELTERS]
    yield
    shelter_service._EMERGENCY_SHELTERS = original


def _base_kwargs() -> dict:
    return {
        "shelter_id": "shelter-101",
        "name": "Community Evacuation Hall",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "capacity": 100,
        "available_capacity": 40,
        "status": ShelterStatus.ACCEPTING_EVACUEES,
    }


def test_valid_emergency_shelter_can_be_created() -> None:
    shelter = EmergencyShelter(**_base_kwargs())
    assert shelter.shelter_id == "shelter-101"


@pytest.mark.parametrize("field, value", [("shelter_id", ""), ("name", "")])
def test_empty_shelter_identity_is_rejected(field: str, value: str) -> None:
    data = _base_kwargs()
    data[field] = value
    with pytest.raises(ValidationError):
        EmergencyShelter(**data)


def test_available_capacity_cannot_exceed_capacity() -> None:
    data = _base_kwargs()
    data["available_capacity"] = 101
    with pytest.raises(ValidationError):
        EmergencyShelter(**data)


def test_shelters_listing_returns_seeded_shelters() -> None:
    response = client.get("/shelters")
    assert response.status_code == 200
    assert len(response.json()) == len(shelter_service._EMERGENCY_SHELTERS)


def test_available_shelters_only_include_accepting_shelters_with_capacity() -> None:
    response = client.get("/available-shelters")
    assert response.status_code == 200
    assert response.json()
    assert all(
        item["status"] in {"ACCEPTING_EVACUEES", "AVAILABLE"}
        and item["available_capacity"] > 0
        for item in response.json()
    )


def test_nearest_shelter_returns_distance() -> None:
    response = client.get(
        "/nearest-shelter", params={"latitude": 12.9716, "longitude": 77.5946}
    )
    assert response.status_code == 200
    assert response.json()["shelter_id"] == "shelter-blr-01"
    assert response.json()["distance_km"] >= 0


def test_capacity_update_changes_available_capacity() -> None:
    response = client.post(
        "/shelters/shelter-blr-01/capacity", json={"available_capacity": 100}
    )
    assert response.status_code == 200
    assert response.json()["available_capacity"] == 100


def test_capacity_update_rejects_capacity_above_limit() -> None:
    response = client.post(
        "/shelters/shelter-blr-01/capacity", json={"available_capacity": 501}
    )
    assert response.status_code == 422


def test_unknown_shelter_capacity_update_returns_404() -> None:
    response = client.post(
        "/shelters/missing-shelter/capacity", json={"available_capacity": 1}
    )
    assert response.status_code == 404
