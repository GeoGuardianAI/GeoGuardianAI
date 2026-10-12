"""API tests for the emergency resource inventory endpoints."""

import pytest
from fastapi.testclient import TestClient

import backend.rescue.services.allocation_service as allocation_service
from backend.rescue.services import emergency_resource_service
import backend.rescue.services.mission_service as mission_service
import backend.rescue.services.rescue_team_service as rescue_team_service
from backend.rescue.api import emergency_resources
from backend.rescue.models.allocation import ResourceAllocationStatus
from backend.rescue.main import app
from backend.rescue.persistence import persist_state

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


_ORIGINAL_ALLOCATIONS = {
    allocation_id: allocation.model_copy(deep=True)
    for allocation_id, allocation in allocation_service._ALLOCATIONS.items()
}
_ORIGINAL_NEXT_ALLOCATION_NUMBER = allocation_service._NEXT_ALLOCATION_NUMBER
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


@pytest.fixture(autouse=True)
def restore_mission_allocation_state() -> None:
    allocation_service._ALLOCATIONS.clear()
    allocation_service._ALLOCATIONS.update(
        {
            allocation_id: allocation.model_copy(deep=True)
            for allocation_id, allocation in _ORIGINAL_ALLOCATIONS.items()
        }
    )
    allocation_service._NEXT_ALLOCATION_NUMBER = _ORIGINAL_NEXT_ALLOCATION_NUMBER

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

    yield

    allocation_service._ALLOCATIONS.clear()
    allocation_service._ALLOCATIONS.update(
        {
            allocation_id: allocation.model_copy(deep=True)
            for allocation_id, allocation in _ORIGINAL_ALLOCATIONS.items()
        }
    )
    allocation_service._NEXT_ALLOCATION_NUMBER = _ORIGINAL_NEXT_ALLOCATION_NUMBER
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


def _create_mission() -> str:
    return mission_service.create_mission(
        team_id="rescue-ny-01",
        disaster_id="disaster-001",
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    ).mission_id


def _mission_allocation_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "mission_id": _create_mission(),
        "resource_id": "resource-food-ny-01",
        "quantity": 100,
    }
    payload.update(overrides)
    return payload


def _create_allocation() -> str:
    response = client.post(
        "/allocate-resource-to-mission",
        json=_mission_allocation_payload(),
    )
    assert response.status_code == 200
    return response.json()["allocation_id"]


def test_release_resource_allocation_returns_released_record() -> None:
    allocation_id = _create_allocation()
    response = client.post(
        "/release-resource-allocation",
        json={"allocation_id": allocation_id},
    )

    assert response.status_code == 200
    assert response.json()["allocation_id"] == allocation_id
    assert response.json()["status"] == "RELEASED"


def test_release_resource_allocation_restores_inventory_quantity() -> None:
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity
    allocation_id = _create_allocation()

    response = client.post(
        "/release-resource-allocation",
        json={"allocation_id": allocation_id},
    )

    assert response.status_code == 200
    assert resource.available_quantity == original_quantity


def test_release_unknown_allocation_returns_404() -> None:
    response = client.post(
        "/release-resource-allocation",
        json={"allocation_id": "missing-allocation"},
    )

    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_release_already_released_allocation_returns_400() -> None:
    allocation_id = _create_allocation()
    first_response = client.post(
        "/release-resource-allocation",
        json={"allocation_id": allocation_id},
    )
    second_response = client.post(
        "/release-resource-allocation",
        json={"allocation_id": allocation_id},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert "already released" in second_response.json()["detail"]


def test_release_cancelled_allocation_returns_400() -> None:
    allocation_id = _create_allocation()
    allocation_service._ALLOCATIONS[allocation_id].status = ResourceAllocationStatus.CANCELLED
    persist_state({"allocations": list(allocation_service._ALLOCATIONS.values())})

    response = client.post(
        "/release-resource-allocation",
        json={"allocation_id": allocation_id},
    )

    assert response.status_code == 400
    assert "cancelled" in response.json()["detail"]


@pytest.mark.parametrize("allocation_id", ["", "   "])
def test_release_invalid_allocation_id_returns_422(allocation_id: str) -> None:
    response = client.post(
        "/release-resource-allocation",
        json={"allocation_id": allocation_id},
    )

    assert response.status_code == 422


def test_release_missing_allocation_id_returns_422() -> None:
    response = client.post("/release-resource-allocation", json={})

    assert response.status_code == 422


def test_failed_release_does_not_mutate_inventory() -> None:
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    allocation_id = _create_allocation()
    client.post(
        "/release-resource-allocation",
        json={"allocation_id": allocation_id},
    )
    restored_quantity = resource.available_quantity

    response = client.post(
        "/release-resource-allocation",
        json={"allocation_id": allocation_id},
    )

    assert response.status_code == 400
    assert resource.available_quantity == restored_quantity


def test_cancel_resource_allocation_returns_cancelled_record() -> None:
    allocation_id = _create_allocation()

    response = client.post(
        "/cancel-resource-allocation",
        json={"allocation_id": allocation_id},
    )

    assert response.status_code == 200
    assert response.json()["allocation_id"] == allocation_id
    assert response.json()["status"] == "CANCELLED"


def test_cancel_resource_allocation_does_not_restore_inventory() -> None:
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    allocation_id = _create_allocation()
    allocated_quantity = resource.available_quantity

    response = client.post(
        "/cancel-resource-allocation",
        json={"allocation_id": allocation_id},
    )

    assert response.status_code == 200
    assert resource.available_quantity == allocated_quantity


def test_cancel_unknown_allocation_returns_404() -> None:
    response = client.post(
        "/cancel-resource-allocation",
        json={"allocation_id": "missing-allocation"},
    )

    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_cancel_already_released_allocation_returns_400() -> None:
    allocation_id = _create_allocation()
    release_response = client.post(
        "/release-resource-allocation",
        json={"allocation_id": allocation_id},
    )
    cancel_response = client.post(
        "/cancel-resource-allocation",
        json={"allocation_id": allocation_id},
    )

    assert release_response.status_code == 200
    assert cancel_response.status_code == 400
    assert "already released" in cancel_response.json()["detail"]


def test_cancel_already_cancelled_allocation_returns_400() -> None:
    allocation_id = _create_allocation()
    first_response = client.post(
        "/cancel-resource-allocation",
        json={"allocation_id": allocation_id},
    )
    second_response = client.post(
        "/cancel-resource-allocation",
        json={"allocation_id": allocation_id},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert "already cancelled" in second_response.json()["detail"]


@pytest.mark.parametrize("allocation_id", ["", "   "])
def test_cancel_invalid_allocation_id_returns_422(allocation_id: str) -> None:
    response = client.post(
        "/cancel-resource-allocation",
        json={"allocation_id": allocation_id},
    )

    assert response.status_code == 422


def test_cancel_missing_allocation_id_returns_422() -> None:
    response = client.post("/cancel-resource-allocation", json={})

    assert response.status_code == 422


def test_failed_cancel_does_not_mutate_allocation_or_inventory() -> None:
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    allocation_id = _create_allocation()
    allocation_service._ALLOCATIONS[allocation_id].status = ResourceAllocationStatus.CANCELLED
    persist_state({"allocations": list(allocation_service._ALLOCATIONS.values())})
    original_allocation = allocation_service._ALLOCATIONS[allocation_id].model_copy(deep=True)
    original_quantity = resource.available_quantity

    response = client.post(
        "/cancel-resource-allocation",
        json={"allocation_id": allocation_id},
    )

    assert response.status_code == 400
    assert allocation_service._ALLOCATIONS[allocation_id] == original_allocation
    assert resource.available_quantity == original_quantity


def test_allocate_resource_to_mission_returns_allocation_record() -> None:
    payload = _mission_allocation_payload()
    response = client.post(
        "/allocate-resource-to-mission",
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert set(data) >= {
        "allocation_id",
        "mission_id",
        "disaster_id",
        "resource_id",
        "quantity",
        "status",
    }
    assert data["mission_id"] == payload["mission_id"]
    assert data["disaster_id"] == "disaster-001"
    assert data["resource_id"] == "resource-food-ny-01"
    assert data["quantity"] == 100
    assert data["status"] == "ALLOCATED"


def test_allocate_resource_to_mission_decreases_resource_quantity() -> None:
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity

    response = client.post(
        "/allocate-resource-to-mission",
        json=_mission_allocation_payload(quantity=100),
    )

    assert response.status_code == 200
    assert resource.available_quantity == original_quantity - 100


def test_completing_mission_releases_allocations_via_api_and_preserves_history() -> None:
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity
    allocation_id = _create_allocation()
    allocation = allocation_service._ALLOCATIONS[allocation_id]
    for status in ("DEPLOYED", "EN_ROUTE", "ARRIVED", "COMPLETED"):
        response = client.patch(
            f"/mission/{allocation.mission_id}/status",
            json={"status": status},
        )
        assert response.status_code == 200
        assert response.json()["status"] == status

    history_response = client.get(f"/mission/{allocation.mission_id}/allocations")

    assert history_response.status_code == 200
    assert len(history_response.json()) == 1
    assert history_response.json()[0]["allocation_id"] == allocation_id
    assert history_response.json()[0]["status"] == "RELEASED"
    assert resource.available_quantity == original_quantity
    assert allocation_service._ALLOCATIONS[allocation_id].status == ResourceAllocationStatus.RELEASED


def test_cancelling_mission_cancels_allocations_without_inventory_restoration_via_api() -> None:
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity
    allocation_id = _create_allocation()
    allocation = allocation_service._ALLOCATIONS[allocation_id]
    allocated_quantity = resource.available_quantity

    response = client.patch(
        f"/mission/{allocation.mission_id}/status",
        json={"status": "CANCELLED"},
    )
    history_response = client.get(f"/mission/{allocation.mission_id}/allocations")

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert history_response.status_code == 200
    assert len(history_response.json()) == 1
    assert history_response.json()[0]["allocation_id"] == allocation_id
    assert history_response.json()[0]["status"] == "CANCELLED"
    assert resource.available_quantity == allocated_quantity
    assert resource.available_quantity == original_quantity - allocation.quantity
    assert allocation_service._ALLOCATIONS[allocation_id].status == ResourceAllocationStatus.CANCELLED


@pytest.mark.parametrize(
    ("terminal_status", "expected_allocation_status", "restores_inventory"),
    [
        ("COMPLETED", ResourceAllocationStatus.RELEASED, True),
        ("CANCELLED", ResourceAllocationStatus.CANCELLED, False),
    ],
)
def test_repeated_terminal_mission_transition_preserves_inventory_and_history_via_api(
    terminal_status: str,
    expected_allocation_status: ResourceAllocationStatus,
    restores_inventory: bool,
) -> None:
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity
    allocation_id = _create_allocation()
    allocation = allocation_service._ALLOCATIONS[allocation_id]
    if terminal_status == "COMPLETED":
        for status in ("DEPLOYED", "EN_ROUTE", "ARRIVED"):
            transition_response = client.patch(
                f"/mission/{allocation.mission_id}/status",
                json={"status": status},
            )
            assert transition_response.status_code == 200

    first_response = client.patch(
        f"/mission/{allocation.mission_id}/status",
        json={"status": terminal_status},
    )
    quantity_after_transition = resource.available_quantity
    repeated_response = client.patch(
        f"/mission/{allocation.mission_id}/status",
        json={"status": terminal_status},
    )
    history_response = client.get(f"/mission/{allocation.mission_id}/allocations")

    assert first_response.status_code == 200
    assert repeated_response.status_code == 400
    assert "Invalid mission status transition" in repeated_response.json()["detail"]
    assert resource.available_quantity == quantity_after_transition
    assert resource.available_quantity == (
        original_quantity if restores_inventory else original_quantity - allocation.quantity
    )
    assert history_response.status_code == 200
    assert len(history_response.json()) == 1
    assert history_response.json()[0]["allocation_id"] == allocation_id
    assert history_response.json()[0]["status"] == expected_allocation_status.value
    assert allocation_service._ALLOCATIONS[allocation_id].status == expected_allocation_status


@pytest.mark.parametrize("terminal_status", ["COMPLETED", "CANCELLED"])
def test_allocate_resource_to_terminal_mission_returns_400_without_inventory_change(
    terminal_status: str,
) -> None:
    mission_id = _create_mission()
    if terminal_status == "COMPLETED":
        for status in ("DEPLOYED", "EN_ROUTE", "ARRIVED"):
            transition_response = client.patch(
                f"/mission/{mission_id}/status",
                json={"status": status},
            )
            assert transition_response.status_code == 200
    client.patch(f"/mission/{mission_id}/status", json={"status": terminal_status})
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity

    response = client.post(
        "/allocate-resource-to-mission",
        json={
            "mission_id": mission_id,
            "resource_id": resource.resource_id,
            "quantity": 100,
        },
    )

    assert response.status_code == 400
    assert "Cannot allocate resources to" in response.json()["detail"]
    assert resource.available_quantity == original_quantity
    assert allocation_service.get_allocations_for_mission(mission_id) == []


def test_allocate_resource_to_mission_unknown_mission_returns_404() -> None:
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity
    original_allocations = {
        allocation_id: allocation.model_copy(deep=True)
        for allocation_id, allocation in allocation_service._ALLOCATIONS.items()
    }

    response = client.post(
        "/allocate-resource-to-mission",
        json={
            "mission_id": "missing-mission",
            "resource_id": "resource-food-ny-01",
            "quantity": 1,
        },
    )

    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]
    assert resource.available_quantity == original_quantity
    assert allocation_service._ALLOCATIONS == original_allocations


def test_allocate_resource_to_mission_unknown_resource_returns_404() -> None:
    payload = _mission_allocation_payload(resource_id="missing-resource")
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity
    original_allocations = {
        allocation_id: allocation.model_copy(deep=True)
        for allocation_id, allocation in allocation_service._ALLOCATIONS.items()
    }

    response = client.post(
        "/allocate-resource-to-mission",
        json=payload,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "no suitable resource available"}
    assert resource.available_quantity == original_quantity
    assert allocation_service._ALLOCATIONS == original_allocations


def test_allocate_resource_to_mission_insufficient_quantity_returns_400() -> None:
    response = client.post(
        "/allocate-resource-to-mission",
        json=_mission_allocation_payload(quantity=3201),
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "requested quantity exceeds available quantity"}


@pytest.mark.parametrize("quantity", [0, -1])
def test_allocate_resource_to_mission_invalid_quantity_returns_422(quantity: int) -> None:
    payload = _mission_allocation_payload(quantity=quantity)
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity
    original_allocations = {
        allocation_id: allocation.model_copy(deep=True)
        for allocation_id, allocation in allocation_service._ALLOCATIONS.items()
    }

    response = client.post(
        "/allocate-resource-to-mission",
        json=payload,
    )

    assert response.status_code == 422
    assert resource.available_quantity == original_quantity
    assert allocation_service._ALLOCATIONS == original_allocations


@pytest.mark.parametrize("missing_field", ["mission_id", "resource_id", "quantity"])
def test_allocate_resource_to_mission_missing_required_field_returns_422(
    missing_field: str,
) -> None:
    payload = {
        "mission_id": "mission-0001",
        "resource_id": "resource-food-ny-01",
        "quantity": 1,
    }
    payload.pop(missing_field)

    response = client.post("/allocate-resource-to-mission", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["mission_id", "resource_id"])
@pytest.mark.parametrize("value", ["", "   "])
def test_allocate_resource_to_mission_empty_identifier_returns_422(
    field: str,
    value: str,
) -> None:
    response = client.post(
        "/allocate-resource-to-mission",
        json=_mission_allocation_payload(**{field: value}),
    )

    assert response.status_code == 422


def test_allocate_resource_to_mission_failed_requests_do_not_mutate_inventory() -> None:
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-food-ny-01"
    )
    original_quantity = resource.available_quantity

    response = client.post(
        "/allocate-resource-to-mission",
        json=_mission_allocation_payload(quantity=original_quantity + 1),
    )

    assert response.status_code == 400
    assert resource.available_quantity == original_quantity


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


def test_mission_resource_recommendations_include_mission_context_and_are_read_only() -> None:
    mission_id = _create_mission()
    original_quantities = {
        resource.resource_id: resource.available_quantity
        for resource in emergency_resource_service._RESOURCES
    }
    original_allocations = {
        allocation_id: allocation.model_copy(deep=True)
        for allocation_id, allocation in allocation_service._ALLOCATIONS.items()
    }

    response = client.post(
        "/recommend-resources-for-mission",
        json={
            "mission_id": mission_id,
            "resource_type": "FOOD",
            "quantity": 100,
        },
    )

    assert response.status_code == 200
    data = response.json()
    mission = mission_service.get_mission(mission_id)
    assert data["mission_id"] == mission_id
    assert data["disaster_id"] == mission.disaster_id
    assert data["destination_latitude"] == mission.destination_latitude
    assert data["destination_longitude"] == mission.destination_longitude
    assert data["resource_type"] == "FOOD"
    assert data["requested_quantity"] == 100
    assert data["recommendation_only"] is True
    assert data["recommended_resources"]
    assert all(
        resource["resource_type"] == "FOOD"
        and resource["available_quantity"] >= 100
        for resource in data["recommended_resources"]
    )
    assert {
        resource.resource_id: resource.available_quantity
        for resource in emergency_resource_service._RESOURCES
    } == original_quantities
    assert allocation_service._ALLOCATIONS == original_allocations


def test_mission_resource_recommendations_reject_unknown_missions() -> None:
    response = client.post(
        "/recommend-resources-for-mission",
        json={"mission_id": "missing-mission"},
    )

    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


@pytest.mark.parametrize("terminal_status", ["CANCELLED", "COMPLETED"])
def test_mission_resource_recommendations_reject_terminal_missions(
    terminal_status: str,
) -> None:
    mission_id = _create_mission()
    if terminal_status == "CANCELLED":
        mission_service.update_mission_status(mission_id, terminal_status)
    else:
        for next_status in ("DEPLOYED", "EN_ROUTE", "ARRIVED", "COMPLETED"):
            mission_service.update_mission_status(mission_id, next_status)

    response = client.post(
        "/recommend-resources-for-mission",
        json={"mission_id": mission_id},
    )

    assert response.status_code == 400
    assert terminal_status.lower() in response.json()["detail"]


@pytest.mark.parametrize(
    "payload",
    [
        {"mission_id": "mission-1", "quantity": 0},
        {"mission_id": "mission-1", "quantity": -1},
        {"mission_id": "mission-1", "quantity": True},
        {"mission_id": "mission-1", "resource_type": "UNKNOWN"},
        {"mission_id": "   "},
    ],
)
def test_mission_resource_recommendations_reject_invalid_filters(
    payload: dict[str, object],
) -> None:
    response = client.post("/recommend-resources-for-mission", json=payload)

    assert response.status_code == 422


def test_mission_resource_recommendations_report_when_no_resource_satisfies_filters() -> None:
    mission_id = _create_mission()

    response = client.post(
        "/recommend-resources-for-mission",
        json={"mission_id": mission_id, "resource_type": "WATER", "quantity": 8000},
    )

    assert response.status_code == 404
    assert "satisfy the requested quantity" in response.json()["detail"]


def test_mission_readiness_reports_stock_and_mission_allocations_without_mutation() -> None:
    mission_id = _create_mission()
    allocation_response = client.post(
        "/allocate-resource-to-mission",
        json={
            "mission_id": mission_id,
            "resource_id": "resource-food-ny-01",
            "quantity": 100,
        },
    )
    assert allocation_response.status_code == 200
    allocation_id = allocation_response.json()["allocation_id"]
    original_quantities = {
        resource.resource_id: resource.available_quantity
        for resource in emergency_resource_service._RESOURCES
    }
    original_allocations = {
        allocation_id: allocation.model_copy(deep=True)
        for allocation_id, allocation in allocation_service._ALLOCATIONS.items()
    }
    response = client.post(
        "/assess-resource-readiness-for-mission",
        json={
            "mission_id": mission_id,
            "requirements": [
                {"resource_type": "FOOD", "quantity": 500},
                {"resource_type": "WATER", "quantity": 500},
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mission_id"] == mission_id
    assert data["disaster_id"] == mission_service.get_mission(mission_id).disaster_id
    assert data["ready"] is True
    assert data["assessment_only"] is True
    food, water = data["requirements"]
    assert food == {
        "resource_type": "FOOD",
        "requested_quantity": 500,
        "inventory_available_quantity": 3100,
        "mission_allocated_quantity": 100,
        "satisfiable": True,
        "shortage": 0,
    }
    assert water["inventory_available_quantity"] == 7200
    assert water["mission_allocated_quantity"] == 0
    assert allocation_id in allocation_service._ALLOCATIONS
    assert {
        resource.resource_id: resource.available_quantity
        for resource in emergency_resource_service._RESOURCES
    } == original_quantities
    assert allocation_service._ALLOCATIONS == original_allocations


def test_mission_readiness_returns_clear_shortage_for_depleted_inventory() -> None:
    mission_id = _create_mission()
    resource = next(
        item
        for item in emergency_resource_service._RESOURCES
        if item.resource_id == "resource-water-la-01"
    )
    resource.available_quantity = 0

    response = client.post(
        "/assess-resource-readiness-for-mission",
        json={
            "mission_id": mission_id,
            "requirements": [{"resource_type": "WATER", "quantity": 20}],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is False
    assert data["requirements"][0]["inventory_available_quantity"] == 0
    assert data["requirements"][0]["mission_allocated_quantity"] == 0
    assert data["requirements"][0]["shortage"] == 20
    assert data["shortages"] == data["requirements"]


def test_mission_readiness_rejects_unknown_mission() -> None:
    response = client.post(
        "/assess-resource-readiness-for-mission",
        json={
            "mission_id": "missing-mission",
            "requirements": [{"resource_type": "FOOD", "quantity": 1}],
        },
    )

    assert response.status_code == 404


@pytest.mark.parametrize("terminal_status", ["CANCELLED", "COMPLETED"])
def test_mission_readiness_rejects_terminal_missions(terminal_status: str) -> None:
    mission_id = _create_mission()
    if terminal_status == "CANCELLED":
        mission_service.update_mission_status(mission_id, terminal_status)
    else:
        for next_status in ("DEPLOYED", "EN_ROUTE", "ARRIVED", "COMPLETED"):
            mission_service.update_mission_status(mission_id, next_status)

    response = client.post(
        "/assess-resource-readiness-for-mission",
        json={
            "mission_id": mission_id,
            "requirements": [{"resource_type": "FOOD", "quantity": 1}],
        },
    )

    assert response.status_code == 400
    assert terminal_status.lower() in response.json()["detail"]


@pytest.mark.parametrize(
    "requirements",
    [
        [],
        [{"resource_type": "FOOD", "quantity": 0}],
        [{"resource_type": "FOOD", "quantity": -1}],
        [{"resource_type": "FOOD", "quantity": True}],
        [{"resource_type": "UNKNOWN", "quantity": 1}],
        [
            {"resource_type": "FOOD", "quantity": 1},
            {"resource_type": "FOOD", "quantity": 2},
        ],
    ],
)
def test_mission_readiness_rejects_invalid_requirements(
    requirements: list[dict[str, object]],
) -> None:
    response = client.post(
        "/assess-resource-readiness-for-mission",
        json={"mission_id": "mission-1", "requirements": requirements},
    )

    assert response.status_code == 422