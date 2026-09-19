"""Unit tests for the deterministic allocation service."""

from datetime import datetime

from pydantic import ValidationError
import pytest

import backend.rescue.services.allocation_service as allocation_service
import backend.rescue.services.emergency_resource_service as emergency_resource_service
import backend.rescue.services.mission_service as mission_service
import backend.rescue.services.rescue_team_service as rescue_team_service
from backend.rescue.models.allocation import AllocationRequest, ResourceAllocationStatus
from backend.rescue.models.hospital import Hospital
from backend.rescue.models.rescue_team import RescueTeam
from backend.rescue.services.allocation_service import (
    NoSuitableRescueTeamError,
    allocate_resource_to_mission,
    get_allocations_for_mission,
    recommend_resources,
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

    allocation = allocate_resource_to_mission(
        mission.mission_id, "resource-food-ny-01", 100
    )

    assert allocation.allocation_id == "allocation-0001"
    assert allocation.resource_id == "resource-food-ny-01"
    assert allocation.quantity == 100
    assert allocation.mission_id == mission.mission_id
    assert allocation.status == ResourceAllocationStatus.ALLOCATED
    assert isinstance(allocation.allocated_at, datetime)
    assert allocation.allocation_id in allocation_service._ALLOCATIONS


def test_mission_linked_allocation_uses_missions_disaster_id() -> None:
    mission = _create_mission("disaster-specific")

    allocation = allocate_resource_to_mission(
        mission.mission_id, "resource-food-ny-01", 100
    )

    assert allocation.disaster_id == "disaster-specific"


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

    with pytest.raises(ValueError, match="no suitable resource available"):
        allocate_resource_to_mission(mission.mission_id, "missing-resource", 100)

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
    with pytest.raises(ValueError, match="does not exist"):
        release_allocation("missing-allocation")


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
    original_allocation = allocation.model_copy(deep=True)
    original_quantity = resource.available_quantity

    with pytest.raises(ValueError):
        release_allocation(allocation.allocation_id)

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
