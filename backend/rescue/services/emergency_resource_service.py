"""Emergency resource inventory service for the Resource & Rescue module.

Provides deterministic in-memory inventory data and read-only lookup helpers
for available emergency resources.
"""

from __future__ import annotations

from backend.rescue.models.emergency_resource import EmergencyResource, ResourceType
from backend.rescue.utils.geo import haversine_km


# Deterministic, realistic mock emergency resources for local testing.
# The list order is used as a stable tie-breaker when distances match.
_RESOURCES: list[EmergencyResource] = [
    EmergencyResource(
        resource_id="resource-food-ny-01",
        name="Emergency Food Rations",
        resource_type=ResourceType.FOOD,
        total_quantity=5000,
        available_quantity=3200,
        latitude=40.7128,
        longitude=-74.0060,
    ),
    EmergencyResource(
        resource_id="resource-water-la-01",
        name="Bottled Drinking Water",
        resource_type=ResourceType.WATER,
        total_quantity=10000,
        available_quantity=7200,
        latitude=34.0522,
        longitude=-118.2437,
    ),
    EmergencyResource(
        resource_id="resource-medical-chi-01",
        name="Emergency Medical Supplies",
        resource_type=ResourceType.MEDICAL_SUPPLIES,
        total_quantity=1800,
        available_quantity=950,
        latitude=41.8781,
        longitude=-87.6298,
    ),
    EmergencyResource(
        resource_id="resource-rescue-hou-01",
        name="Urban Rescue Equipment",
        resource_type=ResourceType.RESCUE_EQUIPMENT,
        total_quantity=600,
        available_quantity=240,
        latitude=29.7604,
        longitude=-95.3698,
    ),
    EmergencyResource(
        resource_id="resource-shelter-mia-01",
        name="Temporary Shelter Kits",
        resource_type=ResourceType.TEMPORARY_SHELTER_SUPPLIES,
        total_quantity=900,
        available_quantity=400,
        latitude=25.7617,
        longitude=-80.1918,
    ),
    EmergencyResource(
        resource_id="resource-water-sea-02",
        name="Depleted Water Reserve",
        resource_type=ResourceType.WATER,
        total_quantity=2500,
        available_quantity=0,
        latitude=47.6062,
        longitude=-122.3321,
    ),
]


def get_available_resources(
    resource_type: ResourceType | None = None,
) -> list[EmergencyResource]:
    """Return resources with positive availability, optionally by type."""
    return [
        resource
        for resource in _RESOURCES
        if resource.available_quantity > 0
        and (resource_type is None or resource.resource_type == resource_type)
    ]


def get_nearby_resources(
    latitude: float,
    longitude: float,
    resource_type: ResourceType | None = None,
) -> list[EmergencyResource]:
    """Return available resources ordered by distance from the coordinates.

    All returned resources are suitable for use because depleted inventory is
    excluded. Ties are resolved by the deterministic in-memory list order.
    """
    _validate_coordinates(latitude, longitude)

    available_resources = get_available_resources(resource_type)
    if not available_resources:
        raise ValueError("no suitable resource available")

    return sorted(
        available_resources,
        key=lambda resource: haversine_km(
            latitude, longitude, resource.latitude, resource.longitude
        ),
    )


def check_available_quantity(resource_id: str, requested_quantity: int) -> bool:
    """Return whether a resource has at least the requested quantity.

    Raises:
        ValueError: If the requested quantity is not a positive integer or the
            resource identifier does not exist in the inventory.
    """
    if (
        not isinstance(requested_quantity, int)
        or isinstance(requested_quantity, bool)
        or requested_quantity <= 0
    ):
        raise ValueError("requested_quantity must be a positive integer")

    resource = next(
        (item for item in _RESOURCES if item.resource_id == resource_id),
        None,
    )
    if resource is None:
        raise ValueError("no suitable resource available")

    return resource.available_quantity >= requested_quantity


def _validate_coordinates(latitude: float, longitude: float) -> None:
    """Validate a geographic coordinate pair for inventory lookups."""
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError("latitude must be between -90 and 90")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError("longitude must be between -180 and 180")