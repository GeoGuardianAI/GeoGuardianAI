"""Emergency resource inventory service for the Resource & Rescue module.

Provides deterministic seeded inventory, SQLite-backed inventory changes, and
read-only lookup helpers for available emergency resources.
"""

from __future__ import annotations

from backend.rescue.models.emergency_resource import EmergencyResource, ResourceType
from backend.rescue.models.audit_event import AuditEventType
from backend.rescue.persistence import load_or_seed, load_records, persist_state, transaction
from backend.rescue.services.audit_service import create_audit_event
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
_RESOURCES = load_or_seed("resources", _RESOURCES, EmergencyResource)


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


def get_recommended_resources(
    latitude: float,
    longitude: float,
    resource_type: ResourceType | None = None,
    minimum_quantity: int | None = None,
) -> list[EmergencyResource]:
    """Return read-only resource recommendations in deterministic rank order.

    A requested type is a strict eligibility filter. Remaining resources rank
    by available quantity descending, geographic distance ascending, resource
    type ascending, and resource identifier ascending.
    """
    if minimum_quantity is not None and (
        not isinstance(minimum_quantity, int)
        or isinstance(minimum_quantity, bool)
        or minimum_quantity <= 0
    ):
        raise ValueError("minimum_quantity must be a positive integer")

    nearby_resources = get_nearby_resources(latitude, longitude, resource_type)
    eligible_resources = [
        resource
        for resource in nearby_resources
        if minimum_quantity is None or resource.available_quantity >= minimum_quantity
    ]
    return sorted(
        eligible_resources,
        key=lambda resource: (
            -resource.available_quantity,
            haversine_km(latitude, longitude, resource.latitude, resource.longitude),
            resource.resource_type.value,
            resource.resource_id,
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


def allocate_resource(
    resource_id: str,
    quantity: int,
    *,
    persist: bool = True,
) -> EmergencyResource:
    """Decrease and return the requested resource inventory quantity."""
    if (
        not isinstance(quantity, int)
        or isinstance(quantity, bool)
        or quantity <= 0
    ):
        raise ValueError("requested_quantity must be a positive integer")

    if not persist:
        resource = next(
            (item for item in _RESOURCES if item.resource_id == resource_id),
            None,
        )
        if resource is None:
            raise ValueError("no suitable resource available")
        if quantity > resource.available_quantity:
            raise ValueError("requested quantity exceeds available quantity")
        resource.available_quantity -= quantity
        return resource

    with transaction() as connection:
        resources = load_records(connection, "resources", EmergencyResource)
        resource = next(
            (item for item in resources if item.resource_id == resource_id),
            None,
        )
        if resource is None:
            raise ValueError("no suitable resource available")
        if quantity > resource.available_quantity:
            raise ValueError("requested quantity exceeds available quantity")
        resource.available_quantity -= quantity
        persist_state(
            {"resources": resources},
            audit_events=[
                create_audit_event(
                    AuditEventType.INVENTORY_ALLOCATED,
                    resource_id=resource_id,
                    summary={
                        "quantity": quantity,
                        "available_quantity_after": resource.available_quantity,
                    },
                )
            ],
        )
    _replace_resource_cache(resources)
    return next(item for item in _RESOURCES if item.resource_id == resource_id)


def _replace_resource_cache(resources: list[EmergencyResource]) -> None:
    """Refresh existing resource instances while preserving references held by services."""
    by_id = {resource.resource_id: resource for resource in _RESOURCES}
    refreshed = []
    for resource in resources:
        cached = by_id.get(resource.resource_id)
        if cached is None:
            refreshed.append(resource)
            continue
        for field_name, value in resource:
            setattr(cached, field_name, value)
        refreshed.append(cached)
    _RESOURCES[:] = refreshed


def _validate_coordinates(latitude: float, longitude: float) -> None:
    """Validate a geographic coordinate pair for inventory lookups."""
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError("latitude must be between -90 and 90")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError("longitude must be between -180 and 180")