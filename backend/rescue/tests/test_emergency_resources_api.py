"""API tests for the emergency resource inventory endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.rescue.services import emergency_resource_service
from backend.rescue.api import emergency_resources
from backend.rescue.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def restore_resource_quantities() -> None:
    original_quantities = {
        resource.resource_id: resource.available_quantity
        for resource in emergency_resource_service._RESOURCES
    }
    yield
    for resource in emergency_resource_service._RESOURCES:
        resource.available_quantity = original_quantities[resource.resource_id]


def test_allocate_resource_inventory_returns_updated_resource() -> None:
    response = client.post(
        "/allocate-resource-inventory",
        json={"resource_id": "resource-food-ny-01", "quantity": 100},
    )

    assert response.status_code == 200
    assert response.json()["resource_id"] == "resource-food-ny-01"
    assert response.json()["available_quantity"] == 3100


def test_allocate_unknown_resource_returns_404() -> None:
    response = client.post(
        "/allocate-resource-inventory",
        json={"resource_id": "unknown-resource", "quantity": 1},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "no suitable resource available"}


def test_allocate_insufficient_quantity_returns_400() -> None:
    response = client.post(
        "/allocate-resource-inventory",
        json={"resource_id": "resource-food-ny-01", "quantity": 3201},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "requested quantity exceeds available quantity"}


@pytest.mark.parametrize("quantity", [0, -1])
def test_allocate_invalid_quantity_returns_422(quantity: int) -> None:
    response = client.post(
        "/allocate-resource-inventory",
        json={"resource_id": "resource-food-ny-01", "quantity": quantity},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("missing_field", ["resource_id", "quantity"])
def test_allocate_missing_required_field_returns_422(missing_field: str) -> None:
    payload = {"resource_id": "resource-food-ny-01", "quantity": 1}
    payload.pop(missing_field)

    response = client.post("/allocate-resource-inventory", json=payload)

    assert response.status_code == 422


def test_available_resources_returns_resource_list() -> None:
    response = client.get("/available-resources")

    assert response.status_code == 200
    assert response.json()
    assert all(item["available_quantity"] > 0 for item in response.json())


def test_resource_type_filtering_returns_requested_type() -> None:
    response = client.get(
        "/available-resources", params={"resource_type": "MEDICAL_SUPPLIES"}
    )

    assert response.status_code == 200
    assert response.json()
    assert all(item["resource_type"] == "MEDICAL_SUPPLIES" for item in response.json())


def test_nearby_resources_returns_ordered_resources() -> None:
    response = client.get(
        "/nearby-resources", params={"latitude": 40.7128, "longitude": -74.0060}
    )

    assert response.status_code == 200
    assert response.json()[0]["resource_id"] == "resource-food-ny-01"


def test_invalid_latitude_returns_422() -> None:
    response = client.get(
        "/nearby-resources", params={"latitude": 90.1, "longitude": -74.0060}
    )

    assert response.status_code == 422


def test_invalid_longitude_returns_422() -> None:
    response = client.get(
        "/nearby-resources", params={"latitude": 40.7128, "longitude": -180.1}
    )

    assert response.status_code == 422


def test_no_suitable_resource_returns_400(monkeypatch) -> None:
    def raise_no_suitable_resource(
        latitude: float, longitude: float, resource_type=None
    ):
        raise ValueError("no suitable resource available")

    monkeypatch.setattr(
        emergency_resources.emergency_resource_service,
        "get_nearby_resources",
        raise_no_suitable_resource,
    )

    response = client.get(
        "/nearby-resources", params={"latitude": 40.7128, "longitude": -74.0060}
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "no suitable resource available"}


def test_resource_response_has_correct_structure() -> None:
    response = client.get("/available-resources")

    assert response.status_code == 200
    assert set(response.json()[0]) == {
        "resource_id",
        "name",
        "resource_type",
        "total_quantity",
        "available_quantity",
        "latitude",
        "longitude",
    }


def test_resource_endpoints_return_correct_http_status_codes() -> None:
    available_response = client.get("/available-resources")
    nearby_response = client.get(
        "/nearby-resources", params={"latitude": 40.7128, "longitude": -74.0060}
    )

    assert available_response.status_code == 200
    assert nearby_response.status_code == 200