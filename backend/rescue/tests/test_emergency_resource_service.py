"""Unit tests for the emergency resource inventory service."""

import pytest

from backend.rescue.models.emergency_resource import ResourceType
from backend.rescue.services import emergency_resource_service


def test_available_resources_are_returned() -> None:
    resources = emergency_resource_service.get_available_resources()

    assert resources
    assert all(resource.available_quantity > 0 for resource in resources)


@pytest.mark.parametrize("resource_type", list(ResourceType))
def test_resource_type_filtering_works(resource_type: ResourceType) -> None:
    resources = emergency_resource_service.get_available_resources(resource_type)

    assert resources
    assert all(resource.resource_type == resource_type for resource in resources)


def test_nearby_resources_are_ordered_by_distance() -> None:
    resources = emergency_resource_service.get_nearby_resources(40.7128, -74.0060)

    assert resources
    assert resources[0].resource_id == "resource-food-ny-01"


def test_depleted_resources_are_ignored() -> None:
    resources = emergency_resource_service.get_nearby_resources(40.7128, -74.0060)

    assert all(resource.resource_id != "resource-water-sea-02" for resource in resources)


@pytest.mark.parametrize("latitude", [-90.1, 90.1])
def test_invalid_latitude_raises_value_error(latitude: float) -> None:
    with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
        emergency_resource_service.get_nearby_resources(latitude, -74.0060)


@pytest.mark.parametrize("longitude", [-180.1, 180.1])
def test_invalid_longitude_raises_value_error(longitude: float) -> None:
    with pytest.raises(ValueError, match="longitude must be between -180 and 180"):
        emergency_resource_service.get_nearby_resources(40.7128, longitude)


def test_no_suitable_resource_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(emergency_resource_service, "_RESOURCES", [])

    with pytest.raises(ValueError, match="no suitable resource available"):
        emergency_resource_service.get_nearby_resources(40.7128, -74.0060)


@pytest.mark.parametrize("requested_quantity", [0, -1])
def test_non_positive_requested_quantity_is_rejected(requested_quantity: int) -> None:
    with pytest.raises(ValueError, match="requested_quantity must be a positive integer"):
        emergency_resource_service.check_available_quantity(
            "resource-food-ny-01", requested_quantity
        )


def test_available_quantity_is_checked() -> None:
    assert emergency_resource_service.check_available_quantity("resource-food-ny-01", 100)
    assert not emergency_resource_service.check_available_quantity(
        "resource-food-ny-01", 5000
    )


def test_unknown_resource_raises_value_error() -> None:
    with pytest.raises(ValueError, match="no suitable resource available"):
        emergency_resource_service.check_available_quantity("unknown-resource", 1)


def test_resource_results_are_deterministic() -> None:
    first = emergency_resource_service.get_nearby_resources(40.7128, -74.0060)
    second = emergency_resource_service.get_nearby_resources(40.7128, -74.0060)

    assert [resource.resource_id for resource in first] == [
        resource.resource_id for resource in second
    ]