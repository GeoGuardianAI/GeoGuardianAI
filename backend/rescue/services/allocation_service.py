"""Resource recommendations and mission-linked allocation management.

This module selects the nearest suitable hospital and ranks available rescue teams
using transparent weighted scoring, and persists mission allocation history and
inventory changes through the rescue SQLite store.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock

from backend.rescue.models.allocation import (
    AllocationRecommendation,
    AllocationRequest,
    MissionResourceReadinessItem,
    MissionResourceReadinessRequest,
    MissionResourceReadinessResponse,
    MissionResourceRecommendation,
    MissionResourceRecommendationRequest,
    ResourceAllocation,
    ResourceAllocationStatus,
)
from backend.rescue.models.audit_event import AuditEventType
from backend.rescue.models.emergency_resource import ResourceType
from backend.rescue.models.mission import Mission, MissionStatus
from backend.rescue.models.hospital import Hospital
from backend.rescue.models.rescue_team import Availability, RescueTeam
from backend.rescue.persistence import (
    load_or_seed,
    load_records,
    next_record_id,
    persist_state,
    transaction,
)
from backend.rescue.services.audit_service import create_audit_event
from backend.rescue.services import emergency_resource_service, mission_service
from backend.rescue.services.hospital_service import get_nearest_hospital
from backend.rescue.services.rescue_team_service import get_available_teams
from backend.rescue.utils.geo import haversine_km

DISTANCE_WEIGHT = 0.45
SPECIALIZATION_WEIGHT = 0.30
TEAM_CAPACITY_WEIGHT = 0.10
AVAILABILITY_WEIGHT = 0.15
SEVERITY_WEIGHT = 0.15
CAPACITY_WEIGHT = TEAM_CAPACITY_WEIGHT
MAX_TEAM_CAPACITY_FOR_SCORING = 25.0
_ALLOCATIONS: dict[str, ResourceAllocation] = {
    allocation.allocation_id: allocation
    for allocation in load_or_seed("allocations", [], ResourceAllocation)
}
_NEXT_ALLOCATION_NUMBER = max(
    (
        int(allocation_id.removeprefix("allocation-"))
        for allocation_id in _ALLOCATIONS
        if allocation_id.startswith("allocation-")
        and allocation_id.removeprefix("allocation-").isdigit()
    ),
    default=0,
) + 1
_MISSION_ALLOCATION_LOCK = RLock()


class ResourceAllocationError(ValueError):
    """Domain-level error raised when no suitable resource can be recommended."""


class NoSuitableHospitalError(ResourceAllocationError):
    """Raised when no suitable hospital is available for the disaster coordinates."""


class NoSuitableRescueTeamError(ResourceAllocationError):
    """Raised when no suitable rescue team is available for the allocation request."""


class NoSuitableEmergencyResourceError(ResourceAllocationError):
    """Raised when no available emergency resource matches the request."""


def _next_allocation_id() -> str:
    """Generate a deterministic allocation ID in a simple incrementing sequence."""
    global _NEXT_ALLOCATION_NUMBER
    allocation_id = f"allocation-{_NEXT_ALLOCATION_NUMBER:04d}"
    _NEXT_ALLOCATION_NUMBER += 1
    return allocation_id


def allocate_resource_to_mission(
    mission_id: str,
    resource_id: str,
    quantity: int,
) -> ResourceAllocation:
    """Allocate inventory to an existing mission and store the allocation record."""
    global _NEXT_ALLOCATION_NUMBER
    with _MISSION_ALLOCATION_LOCK:
        with transaction() as connection:
            if (
                not isinstance(quantity, int)
                or isinstance(quantity, bool)
                or quantity <= 0
            ):
                raise ValueError("requested_quantity must be a positive integer")
            missions = load_records(connection, "missions", Mission)
            mission = next(
                (item for item in missions if item.mission_id == mission_id), None
            )
            if mission is None:
                raise ValueError(f"Mission '{mission_id}' does not exist")
            if mission.status in {MissionStatus.COMPLETED, MissionStatus.CANCELLED}:
                raise ValueError(
                    f"Cannot allocate resources to {mission.status.value.lower()} mission '{mission_id}'"
                )
            resources = load_records(
                connection, "resources", emergency_resource_service.EmergencyResource
            )
            resource = next(
                (item for item in resources if item.resource_id == resource_id), None
            )
            if resource is None:
                raise ValueError("no suitable resource available")
            if quantity > resource.available_quantity:
                raise ValueError("requested quantity exceeds available quantity")
            allocations = load_records(connection, "allocations", ResourceAllocation)
            allocation_id = next_record_id(
                connection, "allocations", "allocation-"
            )
            resource.available_quantity -= quantity
            allocation = ResourceAllocation(
                allocation_id=allocation_id,
                resource_id=resource_id,
                quantity=quantity,
                mission_id=mission.mission_id,
                disaster_id=mission.disaster_id,
                allocated_at=datetime.now(timezone.utc),
                status=ResourceAllocationStatus.ALLOCATED,
            )
            allocations.append(allocation)
            persist_state(
                {"resources": resources, "allocations": allocations},
                audit_events=[
                    create_audit_event(
                        AuditEventType.RESOURCE_ALLOCATED,
                        mission_id=mission.mission_id,
                        disaster_id=mission.disaster_id,
                        resource_id=resource_id,
                        summary={
                            "allocation_id": allocation.allocation_id,
                            "quantity": quantity,
                            "status": allocation.status.value,
                        },
                    )
                ],
            )
        emergency_resource_service._replace_resource_cache(resources)
        _replace_allocation_cache(allocations)
        _NEXT_ALLOCATION_NUMBER = max(
            (
                int(item.allocation_id.removeprefix("allocation-"))
                for item in allocations
                if item.allocation_id.startswith("allocation-")
                and item.allocation_id.removeprefix("allocation-").isdigit()
            ),
            default=0,
        ) + 1
        return allocation


def _replace_allocation_cache(allocations: list[ResourceAllocation]) -> None:
    """Refresh allocation history after a committed write."""
    current = dict(_ALLOCATIONS)
    refreshed: dict[str, ResourceAllocation] = {}
    for allocation in allocations:
        cached = current.get(allocation.allocation_id)
        if cached is not None:
            for field_name, value in allocation:
                setattr(cached, field_name, value)
            refreshed[allocation.allocation_id] = cached
        else:
            refreshed[allocation.allocation_id] = allocation
    _ALLOCATIONS.clear()
    _ALLOCATIONS.update(refreshed)


def release_allocation(allocation_id: str) -> ResourceAllocation:
    """Release an allocation and restore its quantity to the shared inventory."""
    with _MISSION_ALLOCATION_LOCK:
        with transaction() as connection:
            allocations = load_records(connection, "allocations", ResourceAllocation)
            allocation = next(
                (item for item in allocations if item.allocation_id == allocation_id),
                None,
            )
            if allocation is None:
                raise ValueError(f"Allocation '{allocation_id}' does not exist")
            _validate_active_allocation(allocation, "release")
            resources = load_records(
                connection, "resources", emergency_resource_service.EmergencyResource
            )
            resource = next(
                (item for item in resources if item.resource_id == allocation.resource_id),
                None,
            )
            if resource is None:
                raise ValueError(f"Resource '{allocation.resource_id}' does not exist")
            resource.available_quantity += allocation.quantity
            allocation.status = ResourceAllocationStatus.RELEASED
            persist_state(
                {"resources": resources, "allocations": allocations},
                audit_events=[
                    create_audit_event(
                        AuditEventType.RESOURCE_RELEASED,
                        mission_id=allocation.mission_id,
                        disaster_id=allocation.disaster_id,
                        resource_id=allocation.resource_id,
                        summary={
                            "allocation_id": allocation.allocation_id,
                            "quantity": allocation.quantity,
                            "inventory_restored": True,
                        },
                    )
                ],
            )
        emergency_resource_service._replace_resource_cache(resources)
        _replace_allocation_cache(allocations)
        return _ALLOCATIONS[allocation_id]


def cancel_allocation(allocation_id: str) -> ResourceAllocation:
    """Cancel an allocation without restoring its reserved inventory."""
    with _MISSION_ALLOCATION_LOCK:
        with transaction() as connection:
            allocations = load_records(connection, "allocations", ResourceAllocation)
            allocation = next(
                (item for item in allocations if item.allocation_id == allocation_id),
                None,
            )
            if allocation is None:
                raise ValueError(f"Allocation '{allocation_id}' does not exist")
            _validate_active_allocation(allocation, "cancel")
            allocation.status = ResourceAllocationStatus.CANCELLED
            persist_state(
                {"allocations": allocations},
                audit_events=[
                    create_audit_event(
                        AuditEventType.RESOURCE_CANCELLED,
                        mission_id=allocation.mission_id,
                        disaster_id=allocation.disaster_id,
                        resource_id=allocation.resource_id,
                        summary={
                            "allocation_id": allocation.allocation_id,
                            "quantity": allocation.quantity,
                            "inventory_restored": False,
                        },
                    )
                ],
            )
        _replace_allocation_cache(allocations)
        return _ALLOCATIONS[allocation_id]


def _validate_active_allocation(
    allocation: ResourceAllocation,
    operation: str,
) -> None:
    if allocation.status == ResourceAllocationStatus.RELEASED:
        raise ValueError(f"Allocation '{allocation.allocation_id}' is already released")
    if allocation.status == ResourceAllocationStatus.CANCELLED:
        message = (
            "is cancelled and cannot be released"
            if operation == "release"
            else "is already cancelled"
        )
        raise ValueError(f"Allocation '{allocation.allocation_id}' {message}")
    if allocation.status != ResourceAllocationStatus.ALLOCATED:
        verb = "released" if operation == "release" else "cancelled"
        raise ValueError(
            f"Allocation '{allocation.allocation_id}' cannot be {verb} from status {allocation.status.value}"
        )


def settle_mission_allocations(
    mission_id: str,
    terminal_status: MissionStatus,
    *,
    persist: bool = True,
) -> None:
    """Settle active mission allocations on completion or cancellation.

    Completion releases active allocations and restores inventory. Cancellation
    cancels active allocations without restoring inventory, matching the manual
    cancellation contract. Inactive allocation history is left unchanged.
    """
    if terminal_status not in {MissionStatus.COMPLETED, MissionStatus.CANCELLED}:
        raise ValueError("Mission allocations can only be settled at a terminal status")

    with _MISSION_ALLOCATION_LOCK:
        active_allocations = [
            allocation
            for allocation in _ALLOCATIONS.values()
            if allocation.mission_id == mission_id
            and allocation.status == ResourceAllocationStatus.ALLOCATED
        ]
        if terminal_status == MissionStatus.COMPLETED:
            resource_ids = {resource.resource_id for resource in emergency_resource_service._RESOURCES}
            missing_resources = {
                allocation.resource_id
                for allocation in active_allocations
                if allocation.resource_id not in resource_ids
            }
            if missing_resources:
                missing_resource = sorted(missing_resources)[0]
                raise ValueError(f"Resource '{missing_resource}' does not exist")

        original_statuses = {
            allocation.allocation_id: allocation.status
            for allocation in active_allocations
        }
        original_quantities = {
            resource.resource_id: resource.available_quantity
            for resource in emergency_resource_service._RESOURCES
        }
        try:
            for allocation in active_allocations:
                if terminal_status == MissionStatus.COMPLETED:
                    resource = next(
                        item
                        for item in emergency_resource_service._RESOURCES
                        if item.resource_id == allocation.resource_id
                    )
                    resource.available_quantity += allocation.quantity
                    allocation.status = ResourceAllocationStatus.RELEASED
                else:
                    allocation.status = ResourceAllocationStatus.CANCELLED
            if persist:
                persist_state(
                    {
                        "resources": emergency_resource_service._RESOURCES,
                        "allocations": list(_ALLOCATIONS.values()),
                    }
                )
        except Exception:
            for allocation in active_allocations:
                allocation.status = original_statuses[allocation.allocation_id]
            for resource in emergency_resource_service._RESOURCES:
                resource.available_quantity = original_quantities[resource.resource_id]
            raise


def get_allocations_for_mission(mission_id: str) -> list[ResourceAllocation]:
    """Return stored resource allocations for a mission in allocation order."""
    return [
        allocation
        for allocation in _ALLOCATIONS.values()
        if allocation.mission_id == mission_id
    ]


def _score_team(team: RescueTeam, request: AllocationRequest) -> tuple[float, float]:
    """Return the weighted score and geographic distance for a rescue team candidate."""
    distance_km = haversine_km(request.latitude, request.longitude, team.latitude, team.longitude)

    distance_score = max(0.0, 1.0 - (distance_km / 1000.0))
    availability_score = 1.0 if team.availability == Availability.AVAILABLE else 0.0

    specialization_match = 1.0
    if request.required_specialization is not None:
        requested_specialization = request.required_specialization.strip().lower()
        specialization_match = (
            1.0
            if any(item.strip().lower() == requested_specialization for item in team.specialization)
            else 0.0
        )

    capacity_score = min(1.0, team.members / MAX_TEAM_CAPACITY_FOR_SCORING)

    score = (
        DISTANCE_WEIGHT * distance_score
        + SPECIALIZATION_WEIGHT * specialization_match
        + AVAILABILITY_WEIGHT * availability_score
        + TEAM_CAPACITY_WEIGHT * capacity_score
    )
    score *= 1.0 + (request.severity - 1) * SEVERITY_WEIGHT

    return score, distance_km


def recommend_resources(request: AllocationRequest) -> AllocationRecommendation:
    """Return a deterministic recommendation for the nearest hospital and best team.

    The hospital is selected as the nearest hospital to the disaster coordinates.
    The rescue team is selected from the available teams, optionally filtered by the
    required specialization, and ranked by a transparent weighted score based on:
    proximity, specialization match, availability, team capacity, and disaster severity.
    """
    try:
        hospital = get_nearest_hospital(request.latitude, request.longitude)
    except ValueError as exc:
        raise NoSuitableHospitalError(
            f"No suitable hospital found for coordinates ({request.latitude}, {request.longitude})."
        ) from exc

    matched_teams = get_available_teams(
        latitude=request.latitude,
        longitude=request.longitude,
        specialization=request.required_specialization,
    )

    if not matched_teams:
        raise NoSuitableRescueTeamError(
            "No suitable rescue team exists for the requested disaster coordinates and specialization."
        )

    try:
        recommended_resources = emergency_resource_service.get_nearby_resources(
            request.latitude,
            request.longitude,
            request.resource_type,
        )
    except ValueError as exc:
        raise NoSuitableEmergencyResourceError(
            "No suitable emergency resource exists for the requested coordinates and type."
        ) from exc

    scored_teams = [(team, *_score_team(team, request)) for team in matched_teams]
    best_team, score, distance_km = sorted(
        scored_teams,
        key=lambda item: (-item[1], item[2], item[0].team_id),
    )[0]

    priority_score = min(100.0, max(0.0, score * 100.0))
    reasoning_parts = [
        f"Nearest hospital is {hospital.name} ({hospital.hospital_id}).",
        f"Recommended rescue team is {best_team.name} ({best_team.team_id}).",
        (
            f"Estimated team distance is {distance_km:.1f} km and request severity is "
            f"{request.severity}/5."
        ),
    ]
    if request.required_specialization:
        reasoning_parts.append(
            f"Team matches required specialization '{request.required_specialization}'."
        )

    return AllocationRecommendation(
        disaster_id=request.disaster_id,
        recommended_hospital=hospital,
        recommended_rescue_team=best_team,
        recommended_resources=recommended_resources,
        priority_score=round(priority_score, 2),
        reasoning=" ".join(reasoning_parts),
        estimated_distance_km=round(distance_km, 2),
    )


def recommend_resources_for_mission(
    request: MissionResourceRecommendationRequest,
) -> MissionResourceRecommendation:
    """Recommend eligible inventory near a non-terminal mission without allocating it."""
    with _MISSION_ALLOCATION_LOCK:
        mission = mission_service.get_mission(request.mission_id)
        if mission.status in {MissionStatus.COMPLETED, MissionStatus.CANCELLED}:
            raise ValueError(
                f"Cannot recommend resources for {mission.status.value.lower()} "
                f"mission '{mission.mission_id}'"
            )

        try:
            recommended_resources = emergency_resource_service.get_recommended_resources(
                mission.destination_latitude,
                mission.destination_longitude,
                request.resource_type,
                request.quantity,
            )
        except ValueError as exc:
            raise NoSuitableEmergencyResourceError(
                "No available emergency resources match the mission destination and filters."
            ) from exc

        if not recommended_resources:
            raise NoSuitableEmergencyResourceError(
                "No available emergency resources satisfy the requested quantity and type."
            )

        return MissionResourceRecommendation(
            mission_id=mission.mission_id,
            disaster_id=mission.disaster_id,
            destination_latitude=mission.destination_latitude,
            destination_longitude=mission.destination_longitude,
            resource_type=request.resource_type,
            requested_quantity=request.quantity,
            recommended_resources=recommended_resources,
        )


def assess_mission_resource_readiness(
    request: MissionResourceReadinessRequest,
) -> MissionResourceReadinessResponse:
    """Assess explicit mission requirements using on-hand stock plus its active allocations.

    Inventory is reported separately from active allocations: allocation already
    decrements inventory, so the two quantities are disjoint and can be added once
    when determining whether the mission's requirement is covered.
    """
    with _MISSION_ALLOCATION_LOCK:
        mission = mission_service.get_mission(request.mission_id)
        if mission.status in {MissionStatus.COMPLETED, MissionStatus.CANCELLED}:
            raise ValueError(
                f"Cannot assess resource readiness for {mission.status.value.lower()} "
                f"mission '{mission.mission_id}'"
            )

        resources_by_id = {
            resource.resource_id: resource
            for resource in emergency_resource_service._RESOURCES
        }
        active_allocated_by_type: dict[ResourceType, int] = {}
        for allocation in get_allocations_for_mission(mission.mission_id):
            if allocation.status != ResourceAllocationStatus.ALLOCATED:
                continue
            resource = resources_by_id.get(allocation.resource_id)
            if resource is None:
                raise ValueError(
                    f"Resource '{allocation.resource_id}' does not exist"
                )
            active_allocated_by_type[resource.resource_type] = (
                active_allocated_by_type.get(resource.resource_type, 0)
                + allocation.quantity
            )

        results: list[MissionResourceReadinessItem] = []
        for requirement in request.requirements:
            try:
                eligible_inventory = emergency_resource_service.get_recommended_resources(
                    mission.destination_latitude,
                    mission.destination_longitude,
                    requirement.resource_type,
                )
            except ValueError as exc:
                if str(exc) != "no suitable resource available":
                    raise
                eligible_inventory = []

            available_quantity = sum(
                resource.available_quantity for resource in eligible_inventory
            )
            allocated_quantity = active_allocated_by_type.get(
                requirement.resource_type, 0
            )
            shortage = max(
                0,
                requirement.quantity - available_quantity - allocated_quantity,
            )
            results.append(
                MissionResourceReadinessItem(
                    resource_type=requirement.resource_type,
                    requested_quantity=requirement.quantity,
                    inventory_available_quantity=available_quantity,
                    mission_allocated_quantity=allocated_quantity,
                    satisfiable=shortage == 0,
                    shortage=shortage,
                )
            )

        shortages = [item for item in results if not item.satisfiable]
        return MissionResourceReadinessResponse(
            mission_id=mission.mission_id,
            disaster_id=mission.disaster_id,
            mission_status=mission.status,
            ready=not shortages,
            requirements=results,
            shortages=shortages,
        )
