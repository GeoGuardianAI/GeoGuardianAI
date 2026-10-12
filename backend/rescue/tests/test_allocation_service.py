"""Unit tests for the deterministic allocation service."""

from datetime import datetime

from pydantic import ValidationError
import pytest

import backend.rescue.services.allocation_service as allocation_service
import backend.rescue.services.emergency_resource_service as emergency_resource_service
import backend.rescue.services.mission_service as mission_service
import backend.rescue.services.rescue_team_service as rescue_team_service
from backend.rescue.persistence import persist_state
from backend.rescue.models.allocation import (
    AllocationRequest,
    MissionResourceReadinessRequest,
    MissionResourceRecommendationRequest,
    ResourceAllocationStatus,
)
from backend.rescue.models.emergency_resource import ResourceType
from backend.rescue.models.hospital import Hospital
from backend.rescue.models.mission import MissionStatus
from backend.rescue.models.rescue_team import RescueTeam
from backend.rescue.services.allocation_service import (
    NoSuitableRescueTeamError,
    allocate_resource_to_mission,
    assess_mission_resource_readiness,
    cancel_allocation,
    get_allocations_for_mission,
    recommend_resources,
    recommend_resources_for_mission,
    release_allocation,
)


_ORIGINAL_ALLOCATIONS = {
    allocation_id: allocation.model_copy(deep=True)
    for allocation_id, allocation in allocation_service._ALLOCATIONS.items()
}
_ORIGINAL_NEXT_ALLOCATION_NUMBER = allocation_service._NEXT_ALLOCATION_NUMBER
_ORIGINAL_RESOURCE_QUANTITIES = {
    resource.resource_id: resource.available_quantity
    for resource in emergency_resource_service._RESOURCES
}
_ORIGINAL_MISSIONS = {
    mission_id: mission.model_copy(deep=True)
    for mission_id, mission in mission_service._MISSIONS.items()
}
_ORIGINAL_NEXT_MISSION_NUMBER = mission_service._NEXT_MISSION_NUMBER
_ORIGINAL_TEAM_STATE = {
    team.team_id: {
        "availability": team.availability,
        "current_mission_id": team.current_mission_id,
    }
    for team in rescue_team_service._RESCUE_TEAMS
}


def _restore_service_state() -> None:
    allocation_service._ALLOCATIONS.clear()
    allocation_service._ALLOCATIONS.update(
        {
            allocation_id: allocation.model_copy(deep=True)
            for allocation_id, allocation in _ORIGINAL_ALLOCATIONS.items()
        }
    )
    allocation_service._NEXT_ALLOCATION_NUMBER = _ORIGINAL_NEXT_ALLOCATION_NUMBER

    for resource in emergency_resource_service._RESOURCES:
        resource.available_quantity = _ORIGINAL_RESOURCE_QUANTITIES[resource.resource_id]

    mission_service._MISSIONS.clear()
    mission_service._MISSIONS.update(
        {
            mission_id: mission.model_copy(deep=True)
            for mission_id, mission in _ORIGINAL_MISSIONS.items()
        }
    )
    mission_service._NEXT_MISSION_NUMBER = _ORIGINAL_NEXT_MISSION_NUMBER

    for team in rescue_team_service._RESCUE_TEAMS:
        original = _ORIGINAL_TEAM_STATE[team.team_id]
        team.availability = original["availability"]
        team.current_mission_id = original["current_mission_id"]


@pytest.fixture(autouse=True)
def reset_service_state() -> None:
    _restore_service_state()
    yield
    _restore_service_state()


def _create_mission(disaster_id: str = "disaster-001"):
    return mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id=disaster_id,
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )


def _base_request_kwargs() -> dict:
    return {
        "disaster_id": "disaster-001",
        "disaster_type": "flood",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "severity": 3,
        "required_specialization": None,
    }


def test_successful_mission_linked_allocation_is_stored() -> None:
    mission = _create_mission()
    resource_id = "resource-food-ny-01"
    quantity = 100

    allocation = allocate_resource_to_mission(
        mission.mission_id, resource_id, quantity
    )

    assert allocation.allocation_id == "allocation-0001"
    assert allocation.resource_id == resource_id
    assert allocation.quantity == quantity
    assert allocation.mission_id == mission.mission_id
    assert allocation.status == ResourceAllocationStatus.ALLOCATED
    assert isinstance(allocation.allocated_at, datetime)
    assert allocation_service._ALLOCATIONS[allocation.allocation_id] == allocation


def test_mission_linked_allocation_uses_missions_disaster_id() -> None:
    mission = _create_mission("disaster-specific")

    allocation = allocate_resource_to_mission(
        mission.mission_id, "resource-food-ny-01", 100
    )

    assert allocation.disaster_id == mission.disaster_id


def test_mission_linked_allocation_decreases_inventory() -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity

    allocate_resource_to_mission(mission.mission_id, resource.resource_id, 100)

    assert resource.available_quantity == original_quantity - 100


def test_completing_mission_releases_active_allocations_and_preserves_history() -> None:
    mission = _create_mission()
    food = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    water = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-water-la-01"
    )
    original_food = food.available_quantity
    original_water = water.available_quantity
    active_allocation = allocate_resource_to_mission(mission.mission_id, food.resource_id, 100)
    previously_released = allocate_resource_to_mission(mission.mission_id, water.resource_id, 200)
    release_allocation(previously_released.allocation_id)
    allocated_food = food.available_quantity
    allocated_water = water.available_quantity

    for status in ("DEPLOYED", "EN_ROUTE", "ARRIVED", "COMPLETED"):
        mission_service.update_mission_status(mission.mission_id, status)

    history = get_allocations_for_mission(mission.mission_id)
    assert [item.status for item in history] == [
        ResourceAllocationStatus.RELEASED,
        ResourceAllocationStatus.RELEASED,
    ]
    assert active_allocation in history
    assert previously_released in history
    assert food.available_quantity == original_food
    assert water.available_quantity == allocated_water
    assert allocated_food == original_food - 100
    assert allocated_water == original_water


def test_cancelling_mission_cancels_active_allocations_without_restoring_inventory() -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity
    active_allocation = allocate_resource_to_mission(mission.mission_id, resource.resource_id, 100)
    previously_released = allocate_resource_to_mission(mission.mission_id, resource.resource_id, 200)
    release_allocation(previously_released.allocation_id)
    allocated_quantity = resource.available_quantity

    mission_service.update_mission_status(mission.mission_id, "CANCELLED")

    history = get_allocations_for_mission(mission.mission_id)
    assert [item.status for item in history] == [
        ResourceAllocationStatus.CANCELLED,
        ResourceAllocationStatus.RELEASED,
    ]
    assert active_allocation in history
    assert previously_released in history
    assert resource.available_quantity == allocated_quantity
    assert resource.available_quantity == original_quantity - 100


@pytest.mark.parametrize(
    ("terminal_status", "expected_allocation_status", "restores_inventory"),
    [
        ("COMPLETED", ResourceAllocationStatus.RELEASED, True),
        ("CANCELLED", ResourceAllocationStatus.CANCELLED, False),
    ],
)
def test_repeated_terminal_mission_transition_does_not_settle_allocations_twice(
    terminal_status: str,
    expected_allocation_status: ResourceAllocationStatus,
    restores_inventory: bool,
) -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity
    allocation = allocate_resource_to_mission(mission.mission_id, resource.resource_id, 100)
    if terminal_status == "COMPLETED":
        for status in ("DEPLOYED", "EN_ROUTE", "ARRIVED"):
            mission_service.update_mission_status(mission.mission_id, status)

    mission_service.update_mission_status(mission.mission_id, terminal_status)
    quantity_after_transition = resource.available_quantity
    with pytest.raises(ValueError, match="Invalid mission status transition"):
        mission_service.update_mission_status(mission.mission_id, terminal_status)

    assert resource.available_quantity == quantity_after_transition
    assert resource.available_quantity == (
        original_quantity if restores_inventory else original_quantity - 100
    )
    assert get_allocations_for_mission(mission.mission_id) == [allocation]
    assert allocation.status == expected_allocation_status


@pytest.mark.parametrize("terminal_status", ["COMPLETED", "CANCELLED"])
def test_terminal_mission_rejects_new_resource_allocations_without_mutation(
    terminal_status: str,
) -> None:
    mission = _create_mission()
    if terminal_status == "COMPLETED":
        for status in ("DEPLOYED", "EN_ROUTE", "ARRIVED"):
            mission_service.update_mission_status(mission.mission_id, status)
    mission_service.update_mission_status(mission.mission_id, terminal_status)
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity

    with pytest.raises(ValueError, match="Cannot allocate resources to"):
        allocate_resource_to_mission(mission.mission_id, resource.resource_id, 100)

    assert resource.available_quantity == original_quantity
    assert get_allocations_for_mission(mission.mission_id) == []


def test_unknown_mission_fails_without_mutating_inventory_or_records() -> None:
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity

    with pytest.raises(ValueError, match="does not exist"):
        allocate_resource_to_mission("missing-mission", resource.resource_id, 100)

    assert resource.available_quantity == original_quantity
    assert allocation_service._ALLOCATIONS == {}


def test_unknown_resource_fails_without_mutating_inventory_or_records() -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity

    with pytest.raises(ValueError, match="no suitable resource available"):
        allocate_resource_to_mission(mission.mission_id, "missing-resource", 100)

    assert resource.available_quantity == original_quantity
    assert allocation_service._ALLOCATIONS == {}


def test_insufficient_quantity_fails_without_mutating_inventory_or_records() -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity

    with pytest.raises(ValueError, match="requested quantity exceeds available quantity"):
        allocate_resource_to_mission(mission.mission_id, resource.resource_id, original_quantity + 1)

    assert resource.available_quantity == original_quantity
    assert allocation_service._ALLOCATIONS == {}


@pytest.mark.parametrize("quantity", [0, -1, True])
def test_invalid_quantity_fails_without_mutating_inventory_or_records(quantity: int) -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity

    with pytest.raises(ValueError, match="requested_quantity must be a positive integer"):
        allocate_resource_to_mission(mission.mission_id, resource.resource_id, quantity)

    assert resource.available_quantity == original_quantity
    assert allocation_service._ALLOCATIONS == {}


def test_get_allocations_for_mission_returns_records_in_allocation_order() -> None:
    mission = _create_mission()
    first = allocate_resource_to_mission(mission.mission_id, "resource-food-ny-01", 100)
    second = allocate_resource_to_mission(mission.mission_id, "resource-water-la-01", 200)

    allocations = get_allocations_for_mission(mission.mission_id)

    assert allocations == [first, second]


def test_release_allocation_restores_inventory_and_changes_status() -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity
    allocation = allocate_resource_to_mission(mission.mission_id, resource.resource_id, 100)

    released = release_allocation(allocation.allocation_id)

    assert released.status == ResourceAllocationStatus.RELEASED
    assert resource.available_quantity == original_quantity


def test_release_allocation_preserves_record_fields() -> None:
    mission = _create_mission("disaster-release")
    allocation = allocate_resource_to_mission(mission.mission_id, "resource-food-ny-01", 100)
    original_fields = allocation.model_copy(deep=True)

    released = release_allocation(allocation.allocation_id)

    assert released.allocation_id == original_fields.allocation_id
    assert released.mission_id == original_fields.mission_id
    assert released.disaster_id == original_fields.disaster_id
    assert released.resource_id == original_fields.resource_id
    assert released.quantity == original_fields.quantity
    assert released.allocated_at == original_fields.allocated_at


def test_release_unknown_allocation_fails() -> None:
    original_allocations = {
        allocation_id: allocation.model_copy(deep=True)
        for allocation_id, allocation in allocation_service._ALLOCATIONS.items()
    }
    original_resource_quantities = {
        resource.resource_id: resource.available_quantity
        for resource in emergency_resource_service._RESOURCES
    }

    with pytest.raises(ValueError, match="does not exist"):
        release_allocation("missing-allocation")

    assert allocation_service._ALLOCATIONS == original_allocations
    assert {
        resource.resource_id: resource.available_quantity
        for resource in emergency_resource_service._RESOURCES
    } == original_resource_quantities


def test_release_already_released_allocation_fails_without_mutation() -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    allocation = allocate_resource_to_mission(mission.mission_id, resource.resource_id, 100)
    release_allocation(allocation.allocation_id)
    restored_quantity = resource.available_quantity

    with pytest.raises(ValueError, match="already released"):
        release_allocation(allocation.allocation_id)

    assert allocation.status == ResourceAllocationStatus.RELEASED
    assert resource.available_quantity == restored_quantity


def test_release_cancelled_allocation_fails_without_mutation() -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    allocation = allocate_resource_to_mission(mission.mission_id, resource.resource_id, 100)
    allocation.status = ResourceAllocationStatus.CANCELLED
    persist_state({"allocations": list(allocation_service._ALLOCATIONS.values())})
    current_quantity = resource.available_quantity

    with pytest.raises(ValueError, match="cancelled and cannot be released"):
        release_allocation(allocation.allocation_id)

    assert allocation.status == ResourceAllocationStatus.CANCELLED
    assert resource.available_quantity == current_quantity


def test_repeated_release_does_not_restore_inventory_twice() -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    allocation = allocate_resource_to_mission(mission.mission_id, resource.resource_id, 100)
    release_allocation(allocation.allocation_id)
    quantity_after_release = resource.available_quantity

    with pytest.raises(ValueError):
        release_allocation(allocation.allocation_id)

    assert resource.available_quantity == quantity_after_release


def test_failed_release_preserves_allocation_and_resource_state() -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    allocation = allocate_resource_to_mission(mission.mission_id, resource.resource_id, 100)
    allocation.status = ResourceAllocationStatus.CANCELLED
    persist_state({"allocations": list(allocation_service._ALLOCATIONS.values())})
    original_allocation = allocation.model_copy(deep=True)
    original_quantity = resource.available_quantity

    with pytest.raises(ValueError):
        release_allocation(allocation.allocation_id)

    assert allocation == original_allocation
    assert resource.available_quantity == original_quantity


def test_cancel_allocation_changes_allocated_status_without_restoring_inventory() -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    allocation = allocate_resource_to_mission(mission.mission_id, resource.resource_id, 100)
    allocated_quantity = resource.available_quantity

    cancelled = cancel_allocation(allocation.allocation_id)

    assert cancelled.status == ResourceAllocationStatus.CANCELLED
    assert resource.available_quantity == allocated_quantity


def test_cancel_allocation_preserves_record_fields() -> None:
    mission = _create_mission("disaster-cancel")
    allocation = allocate_resource_to_mission(mission.mission_id, "resource-food-ny-01", 100)
    original_fields = allocation.model_copy(deep=True)

    cancelled = cancel_allocation(allocation.allocation_id)

    assert cancelled.allocation_id == original_fields.allocation_id
    assert cancelled.mission_id == original_fields.mission_id
    assert cancelled.disaster_id == original_fields.disaster_id
    assert cancelled.resource_id == original_fields.resource_id
    assert cancelled.quantity == original_fields.quantity
    assert cancelled.allocated_at == original_fields.allocated_at


def test_cancel_unknown_allocation_fails() -> None:
    original_allocations = {
        allocation_id: allocation.model_copy(deep=True)
        for allocation_id, allocation in allocation_service._ALLOCATIONS.items()
    }
    original_resource_quantities = {
        resource.resource_id: resource.available_quantity
        for resource in emergency_resource_service._RESOURCES
    }

    with pytest.raises(ValueError, match="does not exist"):
        cancel_allocation("missing-allocation")

    assert allocation_service._ALLOCATIONS == original_allocations
    assert {
        resource.resource_id: resource.available_quantity
        for resource in emergency_resource_service._RESOURCES
    } == original_resource_quantities


def test_cancel_released_allocation_fails_without_mutation() -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    allocation = allocate_resource_to_mission(mission.mission_id, resource.resource_id, 100)
    release_allocation(allocation.allocation_id)
    original_allocation = allocation.model_copy(deep=True)
    original_quantity = resource.available_quantity

    with pytest.raises(ValueError, match="already released"):
        cancel_allocation(allocation.allocation_id)

    assert allocation == original_allocation
    assert resource.available_quantity == original_quantity


def test_cancel_already_cancelled_allocation_fails_without_mutation() -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    allocation = allocate_resource_to_mission(mission.mission_id, resource.resource_id, 100)
    cancel_allocation(allocation.allocation_id)
    original_allocation = allocation.model_copy(deep=True)
    original_quantity = resource.available_quantity

    with pytest.raises(ValueError, match="already cancelled"):
        cancel_allocation(allocation.allocation_id)

    assert allocation == original_allocation
    assert resource.available_quantity == original_quantity


def test_valid_disaster_produces_an_allocation_recommendation() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert recommendation is not None
    assert recommendation.disaster_id == "disaster-001"


def test_recommended_hospital_is_a_hospital_instance() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert isinstance(recommendation.recommended_hospital, Hospital)


def test_recommended_rescue_team_is_a_rescueteam_instance() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert isinstance(recommendation.recommended_rescue_team, RescueTeam)


def test_recommendation_contains_correct_disaster_id() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert recommendation.disaster_id == request.disaster_id


def test_recommended_resources_are_ranked_by_nearest_eligible_resource() -> None:
    request = AllocationRequest(**_base_request_kwargs())

    recommendation = recommend_resources(request)

    assert recommendation.recommended_resources[0].resource_id == "resource-food-ny-01"
    assert all(resource.available_quantity > 0 for resource in recommendation.recommended_resources)


def test_recommended_resources_exclude_insufficient_inventory() -> None:
    request = AllocationRequest(**_base_request_kwargs())

    recommendation = recommend_resources(request)

    assert all(
        resource.resource_id != "resource-water-sea-02"
        for resource in recommendation.recommended_resources
    )


def test_recommended_resources_respect_requested_resource_type() -> None:
    request = AllocationRequest(
        **{**_base_request_kwargs(), "resource_type": ResourceType.WATER}
    )

    recommendation = recommend_resources(request)

    assert recommendation.recommended_resources
    assert all(
        resource.resource_type == ResourceType.WATER
        for resource in recommendation.recommended_resources
    )
    assert recommendation.recommended_resources[0].resource_id == "resource-water-la-01"


def test_invalid_recommendation_coordinates_are_rejected() -> None:
    with pytest.raises(ValidationError):
        AllocationRequest(**{**_base_request_kwargs(), "latitude": 90.1})


def test_priority_score_is_between_0_and_100() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert 0 <= recommendation.priority_score <= 100


def test_estimated_distance_is_non_negative() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert recommendation.estimated_distance_km >= 0


def test_reasoning_is_non_empty() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert recommendation.reasoning.strip() != ""


def test_required_specialization_causes_service_to_select_matching_team() -> None:
    request = AllocationRequest(**{**_base_request_kwargs(), "required_specialization": "search"})
    recommendation = recommend_resources(request)

    assert "search" in [item.lower() for item in recommendation.recommended_rescue_team.specialization]


def test_unavailable_team_is_never_selected() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    recommendation = recommend_resources(request)

    assert recommendation.recommended_rescue_team.availability.value == "AVAILABLE"


def test_when_no_suitable_specialization_exists_a_clear_domain_exception_is_raised() -> None:
    request = AllocationRequest(**{**_base_request_kwargs(), "required_specialization": "nonexistent-skill"})

    with pytest.raises(NoSuitableRescueTeamError, match="No suitable rescue team exists"):
        recommend_resources(request)


@pytest.mark.parametrize("latitude", [-90.1, 90.1])
def test_invalid_latitude_is_rejected(latitude: float) -> None:
    data = _base_request_kwargs()
    data["latitude"] = latitude

    with pytest.raises(ValidationError):
        AllocationRequest(**data)


@pytest.mark.parametrize("longitude", [-180.1, 180.1])
def test_invalid_longitude_is_rejected(longitude: float) -> None:
    data = _base_request_kwargs()
    data["longitude"] = longitude

    with pytest.raises(ValidationError):
        AllocationRequest(**data)


def test_same_input_produces_the_same_recommendation() -> None:
    request = AllocationRequest(**_base_request_kwargs())
    first = recommend_resources(request)
    second = recommend_resources(request)

    assert first == second


def test_mission_recommendation_uses_mission_coordinates_and_disaster_id() -> None:
    mission = _create_mission("disaster-mission-resource")
    request = MissionResourceRecommendationRequest(
        mission_id=mission.mission_id,
        resource_type=ResourceType.FOOD,
        quantity=100,
    )

    recommendation = recommend_resources_for_mission(request)

    assert recommendation.mission_id == mission.mission_id
    assert recommendation.disaster_id == mission.disaster_id
    assert recommendation.destination_latitude == mission.destination_latitude
    assert recommendation.destination_longitude == mission.destination_longitude
    assert recommendation.resource_type == ResourceType.FOOD
    assert recommendation.requested_quantity == 100
    assert recommendation.recommendation_only is True


def test_mission_recommendation_filters_type_quantity_and_depleted_resources() -> None:
    mission = _create_mission()
    recommendation = recommend_resources_for_mission(
        MissionResourceRecommendationRequest(
            mission_id=mission.mission_id,
            resource_type=ResourceType.WATER,
            quantity=1000,
        )
    )

    assert [resource.resource_id for resource in recommendation.recommended_resources] == [
        "resource-water-la-01"
    ]
    assert all(
        resource.resource_type == ResourceType.WATER
        and resource.available_quantity >= 1000
        and resource.available_quantity > 0
        for resource in recommendation.recommended_resources
    )


def test_mission_recommendations_use_quantity_then_distance_then_type_and_id_order() -> None:
    mission = _create_mission()
    resources = {
        resource.resource_id: resource
        for resource in emergency_resource_service._RESOURCES
    }
    for resource in resources.values():
        resource.available_quantity = 0

    resources["resource-food-ny-01"].available_quantity = 50
    resources["resource-medical-chi-01"].available_quantity = 50
    resources["resource-rescue-hou-01"].available_quantity = 50
    resources["resource-water-la-01"].available_quantity = 100
    resources["resource-food-ny-01"].latitude = mission.destination_latitude
    resources["resource-food-ny-01"].longitude = mission.destination_longitude
    resources["resource-medical-chi-01"].latitude = mission.destination_latitude
    resources["resource-medical-chi-01"].longitude = mission.destination_longitude
    resources["resource-water-la-01"].latitude = 41.0
    resources["resource-rescue-hou-01"].latitude = 42.0

    recommendation = recommend_resources_for_mission(
        MissionResourceRecommendationRequest(mission_id=mission.mission_id)
    )

    assert [resource.resource_id for resource in recommendation.recommended_resources] == [
        "resource-water-la-01",
        "resource-food-ny-01",
        "resource-medical-chi-01",
        "resource-rescue-hou-01",
    ]
    assert recommendation.ranking_order == (
        "strict resource-type filter; available quantity descending; "
        "geographic distance ascending; resource type ascending; resource ID ascending"
    )


def test_mission_recommendations_do_not_mutate_inventory_or_allocations() -> None:
    mission = _create_mission()
    original_quantities = {
        resource.resource_id: resource.available_quantity
        for resource in emergency_resource_service._RESOURCES
    }
    original_allocations = {
        allocation_id: allocation.model_copy(deep=True)
        for allocation_id, allocation in allocation_service._ALLOCATIONS.items()
    }

    recommend_resources_for_mission(
        MissionResourceRecommendationRequest(mission_id=mission.mission_id)
    )

    assert {
        resource.resource_id: resource.available_quantity
        for resource in emergency_resource_service._RESOURCES
    } == original_quantities
    assert allocation_service._ALLOCATIONS == original_allocations


def test_mission_recommendations_reject_unknown_and_terminal_missions() -> None:
    with pytest.raises(ValueError, match="does not exist"):
        recommend_resources_for_mission(
            MissionResourceRecommendationRequest(mission_id="missing-mission")
        )

    mission = _create_mission()
    mission_service.update_mission_status(mission.mission_id, MissionStatus.CANCELLED)
    with pytest.raises(ValueError, match="cancelled mission"):
        recommend_resources_for_mission(
            MissionResourceRecommendationRequest(mission_id=mission.mission_id)
        )


def test_readiness_counts_inventory_and_active_allocations_separately_once() -> None:
    mission = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    allocate_resource_to_mission(mission.mission_id, resource.resource_id, 100)

    result = assess_mission_resource_readiness(
        MissionResourceReadinessRequest(
            mission_id=mission.mission_id,
            requirements=[{"resource_type": "FOOD", "quantity": 3200}],
        )
    )

    requirement = result.requirements[0]
    assert result.ready is True
    assert requirement.inventory_available_quantity == 3100
    assert requirement.mission_allocated_quantity == 100
    assert requirement.satisfiable is True
    assert requirement.shortage == 0


def test_readiness_reports_shortage_and_depleted_type_across_multiple_requirements() -> None:
    mission = _create_mission()
    depleted_resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-water-la-01"
    )
    depleted_resource.available_quantity = 0
    result = assess_mission_resource_readiness(
        MissionResourceReadinessRequest(
            mission_id=mission.mission_id,
            requirements=[
                {"resource_type": "WATER", "quantity": 100},
                {"resource_type": "MEDICAL_SUPPLIES", "quantity": 2000},
                {"resource_type": "FOOD", "quantity": 100},
            ],
        )
    )

    assert result.ready is False
    assert [item.resource_type for item in result.requirements] == [
        ResourceType.WATER,
        ResourceType.MEDICAL_SUPPLIES,
        ResourceType.FOOD,
    ]
    assert result.requirements[0].inventory_available_quantity == 0
    assert result.requirements[0].shortage == 100
    assert result.requirements[1].inventory_available_quantity == 950
    assert result.requirements[1].shortage == 1050
    assert result.requirements[2].satisfiable is True
    assert [item.resource_type for item in result.shortages] == [
        ResourceType.WATER,
        ResourceType.MEDICAL_SUPPLIES,
    ]


def test_readiness_ignores_inactive_allocations() -> None:
    mission = _create_mission()
    allocation = allocate_resource_to_mission(
        mission.mission_id, "resource-food-ny-01", 100
    )
    release_allocation(allocation.allocation_id)

    result = assess_mission_resource_readiness(
        MissionResourceReadinessRequest(
            mission_id=mission.mission_id,
            requirements=[{"resource_type": "FOOD", "quantity": 3200}],
        )
    )

    assert result.requirements[0].inventory_available_quantity == 3200
    assert result.requirements[0].mission_allocated_quantity == 0
    assert result.ready is True
