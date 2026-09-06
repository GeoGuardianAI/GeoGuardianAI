"""Unit tests for the `EmergencyResource` Pydantic model."""

from pydantic import ValidationError
import pytest

from backend.rescue.models.emergency_resource import EmergencyResource, ResourceType


def _base_kwargs() -> dict:
    return {
        "resource_id": "resource-101",
        "name": "Emergency Water",
        "resource_type": ResourceType.WATER,
        "total_quantity": 1000,
        "available_quantity": 750,
        "latitude": 40.0,
        "longitude": -70.0,
    }


def test_valid_emergency_resource_can_be_created() -> None:
    resource = EmergencyResource(**_base_kwargs())
    assert resource.resource_id == "resource-101"
    assert resource.name == "Emergency Water"


@pytest.mark.parametrize("resource_type", list(ResourceType))
def test_each_resource_type_works(resource_type: ResourceType) -> None:
    data = _base_kwargs()
    data["resource_type"] = resource_type
    resource = EmergencyResource(**data)
    assert resource.resource_type == resource_type


def test_zero_quantities_are_valid() -> None:
    data = _base_kwargs()
    data["total_quantity"] = 0
    data["available_quantity"] = 0
    resource = EmergencyResource(**data)
    assert resource.total_quantity == 0
    assert resource.available_quantity == 0


def test_negative_total_quantity_is_rejected() -> None:
    data = _base_kwargs()
    data["total_quantity"] = -1
    with pytest.raises(ValidationError):
        EmergencyResource(**data)


def test_negative_available_quantity_is_rejected() -> None:
    data = _base_kwargs()
    data["available_quantity"] = -1
    with pytest.raises(ValidationError):
        EmergencyResource(**data)


def test_available_quantity_greater_than_total_is_rejected() -> None:
    data = _base_kwargs()
    data["total_quantity"] = 10
    data["available_quantity"] = 11
    with pytest.raises(ValidationError):
        EmergencyResource(**data)


@pytest.mark.parametrize("latitude", [90.1, -90.1, 100.0])
def test_invalid_latitude_is_rejected(latitude: float) -> None:
    data = _base_kwargs()
    data["latitude"] = latitude
    with pytest.raises(ValidationError):
        EmergencyResource(**data)


@pytest.mark.parametrize("longitude", [180.1, -180.1, 200.0])
def test_invalid_longitude_is_rejected(longitude: float) -> None:
    data = _base_kwargs()
    data["longitude"] = longitude
    with pytest.raises(ValidationError):
        EmergencyResource(**data)