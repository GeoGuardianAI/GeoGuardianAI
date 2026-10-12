"""API tests for the mission endpoints."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.rescue.services.allocation_service as allocation_service
import backend.rescue.services.emergency_resource_service as emergency_resource_service
import backend.rescue.services.mission_service as mission_service
import backend.rescue.services.risk_priority_service as risk_priority_service
import backend.rescue.services.rescue_team_service as rescue_team_service
from backend.rescue.api.missions import router as missions_router
from backend.rescue.api.risk_priority import router as risk_priority_router

app = FastAPI()
app.include_router(missions_router)
app.include_router(risk_priority_router)
client = TestClient(app)

_ORIGINAL_TEAM_STATE = {
    team.team_id: {
        "availability": team.availability,
        "current_mission_id": team.current_mission_id,
    }
    for team in rescue_team_service._RESCUE_TEAMS
}
_ORIGINAL_MISSIONS = {
    mission_id: mission.model_copy(deep=True)
    for mission_id, mission in mission_service._MISSIONS.items()
}
_ORIGINAL_NEXT_MISSION_NUMBER = mission_service._NEXT_MISSION_NUMBER
_ORIGINAL_ALLOCATIONS = {
    allocation_id: allocation.model_copy(deep=True)
    for allocation_id, allocation in allocation_service._ALLOCATIONS.items()
}
_ORIGINAL_NEXT_ALLOCATION_NUMBER = allocation_service._NEXT_ALLOCATION_NUMBER
_ORIGINAL_RESOURCE_QUANTITIES = {
    resource.resource_id: resource.available_quantity
    for resource in emergency_resource_service._RESOURCES
}


def _restore_team_state() -> None:
    for team in rescue_team_service._RESCUE_TEAMS:
        original = _ORIGINAL_TEAM_STATE.get(team.team_id)
        if original is None:
            team.availability = rescue_team_service.Availability.AVAILABLE
            team.current_mission_id = None
            continue

        team.availability = original["availability"]
        team.current_mission_id = original["current_mission_id"]


@pytest.fixture(autouse=True)
def reset_state() -> None:
    """Reset mission and shared rescue-team state before and after each test."""
    original_risk_results = risk_priority_service._RISK_PRIORITY_RESULTS.copy()
    risk_priority_service._RISK_PRIORITY_RESULTS.clear()
    _restore_team_state()
    mission_service._MISSIONS.clear()
    mission_service._MISSIONS.update({
        mission_id: mission.model_copy(deep=True)
        for mission_id, mission in _ORIGINAL_MISSIONS.items()
    })
    mission_service._NEXT_MISSION_NUMBER = _ORIGINAL_NEXT_MISSION_NUMBER
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

    yield

    mission_service._MISSIONS.clear()
    mission_service._MISSIONS.update({
        mission_id: mission.model_copy(deep=True)
        for mission_id, mission in _ORIGINAL_MISSIONS.items()
    })
    mission_service._NEXT_MISSION_NUMBER = _ORIGINAL_NEXT_MISSION_NUMBER
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
    _restore_team_state()
    risk_priority_service._RISK_PRIORITY_RESULTS.clear()
    risk_priority_service._RISK_PRIORITY_RESULTS.update(original_risk_results)


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "team_id": "rescue-ny-01",
        "disaster_id": "disaster-001",
        "destination_latitude": 40.7128,
        "destination_longitude": -74.0060,
    }
    payload.update(overrides)
    return payload


def test_post_mission_valid_request_returns_http_201() -> None:
    response = client.post("/mission", json=_valid_payload())
    assert response.status_code == 201


def test_post_mission_response_contains_valid_mission_object() -> None:
    response = client.post("/mission", json=_valid_payload())
    data = response.json()

    assert isinstance(data, dict)
    assert set(data.keys()) >= {
        "mission_id",
        "disaster_id",
        "team_id",
        "destination_latitude",
        "destination_longitude",
        "priority",
        "status",
        "created_at",
        "hospital_id",
        "vehicle_id",
    }


def test_post_mission_response_includes_required_fields() -> None:
    response = client.post("/mission", json=_valid_payload())
    data = response.json()

    assert "mission_id" in data
    assert "disaster_id" in data
    assert "team_id" in data
    assert "destination_latitude" in data
    assert "destination_longitude" in data
    assert "priority" in data
    assert "status" in data
    assert "created_at" in data


def test_post_mission_defaults_priority_to_medium_when_omitted() -> None:
    response = client.post("/mission", json=_valid_payload())
    assert response.status_code == 201
    assert response.json()["priority"] == "MEDIUM"


def test_post_mission_newly_created_mission_starts_assigned() -> None:
    response = client.post("/mission", json=_valid_payload())
    assert response.status_code == 201
    assert response.json()["status"] == "ASSIGNED"


def test_post_mission_accepts_hospital_id_none() -> None:
    response = client.post("/mission", json=_valid_payload(hospital_id=None))
    assert response.status_code == 201
    assert response.json()["hospital_id"] is None


def test_post_mission_accepts_vehicle_id_none() -> None:
    response = client.post("/mission", json=_valid_payload(vehicle_id=None))
    assert response.status_code == 201
    assert response.json()["vehicle_id"] is None


def test_post_mission_preserves_provided_hospital_id() -> None:
    response = client.post("/mission", json=_valid_payload(hospital_id="hosp-123"))
    assert response.status_code == 201
    assert response.json()["hospital_id"] == "hosp-123"


def test_post_mission_preserves_provided_vehicle_id() -> None:
    response = client.post("/mission", json=_valid_payload(vehicle_id="vehicle-456"))
    assert response.status_code == 201
    assert response.json()["vehicle_id"] == "vehicle-456"


def test_post_mission_invalid_destination_latitude_returns_422() -> None:
    response = client.post("/mission", json=_valid_payload(destination_latitude=90.1))
    assert response.status_code == 422


def test_post_mission_invalid_destination_longitude_returns_422() -> None:
    response = client.post("/mission", json=_valid_payload(destination_longitude=180.1))
    assert response.status_code == 422


def test_post_mission_missing_team_id_returns_422() -> None:
    payload = _valid_payload()
    payload.pop("team_id")
    response = client.post("/mission", json=payload)
    assert response.status_code == 422


def test_post_mission_missing_disaster_id_returns_422() -> None:
    payload = _valid_payload()
    payload.pop("disaster_id")
    response = client.post("/mission", json=payload)
    assert response.status_code == 422


def test_post_mission_invalid_priority_returns_422() -> None:
    response = client.post("/mission", json=_valid_payload(priority="INVALID"))
    assert response.status_code == 422


def test_post_mission_nonexistent_team_returns_http_400() -> None:
    response = client.post("/mission", json=_valid_payload(team_id="missing-team"))
    assert response.status_code == 400
    assert "detail" in response.json()
    assert "does not exist" in response.json()["detail"]


def test_post_mission_unavailable_team_returns_http_400() -> None:
    response = client.post("/mission", json=_valid_payload(team_id="rescue-hou-01"))
    assert response.status_code == 400
    assert "detail" in response.json()
    assert "not available" in response.json()["detail"]


def test_get_mission_returns_created_mission() -> None:
    create_response = client.post("/mission", json=_valid_payload())
    created = create_response.json()

    response = client.get(f"/mission/{created['mission_id']}")

    assert response.status_code == 200
    assert response.json()["mission_id"] == created["mission_id"]


def test_list_missions_returns_created_missions_in_order() -> None:
    first_response = client.post("/mission", json=_valid_payload())
    second_response = client.post(
        "/mission",
        json=_valid_payload(team_id="rescue-chi-01", disaster_id="disaster-002"),
    )

    response = client.get("/missions")

    assert response.status_code == 200
    assert [mission["mission_id"] for mission in response.json()] == [
        first_response.json()["mission_id"],
        second_response.json()["mission_id"],
    ]


def test_get_ranked_missions_returns_rank_and_explicit_missing_risk_data() -> None:
    lower_priority = client.post(
        "/mission",
        json=_valid_payload(priority="LOW"),
    )
    higher_priority = client.post(
        "/mission",
        json=_valid_payload(team_id="rescue-chi-01", priority="HIGH", disaster_id="disaster-002"),
    )
    assert lower_priority.status_code == 201
    assert higher_priority.status_code == 201

    response = client.get("/missions/ranked")

    assert response.status_code == 200
    data = response.json()
    assert data["risk_data_available"] is False
    assert data["missing_risk_disaster_ids"] == ["disaster-001", "disaster-002"]
    assert "disaster risk unassessed" in data["ranking_basis"]
    assert [item["rank"] for item in data["missions"]] == [1, 2]
    assert [item["mission"]["mission_id"] for item in data["missions"]] == [
        higher_priority.json()["mission_id"],
        lower_priority.json()["mission_id"],
    ]
    assert [item["mission"]["priority"] for item in data["missions"]] == ["HIGH", "LOW"]
    assert [item["disaster_risk_score"] for item in data["missions"]] == [None, None]


def test_get_ranked_missions_returns_empty_ranked_list_when_no_missions_exist() -> None:
    response = client.get("/missions/ranked")

    assert response.status_code == 200
    assert response.json() == {
        "risk_data_available": False,
        "missing_risk_disaster_ids": [],
        "ranking_basis": (
            "manual mission priority descending, active status before terminal status "
            "in lifecycle order, creation time oldest first, mission ID ascending; "
            "disaster risk unassessed"
        ),
        "missions": [],
    }


def test_get_ranked_missions_uses_risk_scores_calculated_for_matching_disaster_ids() -> None:
    high_risk_mission = client.post(
        "/mission",
        json=_valid_payload(
            disaster_id="disaster-calculated",
            priority="LOW",
        ),
    )
    second_mission_same_disaster = client.post(
        "/mission",
        json=_valid_payload(
            team_id="rescue-chi-01",
            disaster_id="disaster-calculated",
            priority="MEDIUM",
        ),
    )
    unassessed_mission = client.post(
        "/mission",
        json=_valid_payload(
            team_id="rescue-miami-01",
            disaster_id="disaster-unassessed",
            priority="CRITICAL",
        ),
    )
    assert high_risk_mission.status_code == 201
    assert second_mission_same_disaster.status_code == 201
    assert unassessed_mission.status_code == 201

    calculated_risk = client.post(
        "/risk-priority",
        json={
            "disaster_id": "disaster-calculated",
            "disaster_type": "flood",
            "latitude": 12.0,
            "longitude": 77.0,
            "severity": 4,
            "affected_population": 5000,
            "critical_infrastructure": False,
        },
    )

    response = client.get("/missions/ranked")

    assert calculated_risk.status_code == 200
    assert calculated_risk.json()["risk_score"] == 52.5
    assert response.status_code == 200
    data = response.json()
    assert data["risk_data_available"] is True
    assert data["missing_risk_disaster_ids"] == ["disaster-unassessed"]
    assert [item["mission"]["mission_id"] for item in data["missions"]] == [
        second_mission_same_disaster.json()["mission_id"],
        high_risk_mission.json()["mission_id"],
        unassessed_mission.json()["mission_id"],
    ]
    assert [item["disaster_risk_score"] for item in data["missions"]] == [
        52.5,
        52.5,
        None,
    ]


def test_invalid_risk_calculation_inputs_leave_missions_unassessed() -> None:
    created = client.post("/mission", json=_valid_payload(disaster_id="disaster-needs-input"))
    assert created.status_code == 201

    rejected_risk = client.post(
        "/risk-priority",
        json={
            "disaster_id": "disaster-needs-input",
            "disaster_type": "flood",
            "latitude": 12.0,
            "longitude": 77.0,
        },
    )
    ranking_response = client.get("/missions/ranked")

    assert rejected_risk.status_code == 422
    assert ranking_response.status_code == 200
    data = ranking_response.json()
    assert data["risk_data_available"] is False
    assert data["missing_risk_disaster_ids"] == ["disaster-needs-input"]
    assert data["missions"][0]["mission"]["mission_id"] == created.json()["mission_id"]
    assert data["missions"][0]["disaster_risk_score"] is None


def test_get_mission_unknown_id_returns_http_404() -> None:
    response = client.get("/mission/unknown-mission-id")
    assert response.status_code == 404
    assert "detail" in response.json()


def test_get_mission_retrieved_values_match_created_mission() -> None:
    create_response = client.post("/mission", json=_valid_payload(hospital_id="hosp-99", vehicle_id="veh-99"))
    created = create_response.json()

    response = client.get(f"/mission/{created['mission_id']}")
    retrieved = response.json()

    assert response.status_code == 200
    for key in (
        "mission_id",
        "disaster_id",
        "team_id",
        "hospital_id",
        "vehicle_id",
        "destination_latitude",
        "destination_longitude",
        "priority",
        "status",
        "created_at",
    ):
        assert retrieved[key] == created[key]


def test_get_mission_allocations_returns_one_allocation() -> None:
    create_response = client.post("/mission", json=_valid_payload())
    mission_id = create_response.json()["mission_id"]
    allocation = allocation_service.allocate_resource_to_mission(
        mission_id, "resource-food-ny-01", 100
    )

    response = client.get(f"/mission/{mission_id}/allocations")

    assert response.status_code == 200
    assert response.json() == [allocation.model_dump(mode="json")]


def test_get_mission_allocations_returns_records_in_allocation_order() -> None:
    create_response = client.post("/mission", json=_valid_payload())
    mission_id = create_response.json()["mission_id"]
    first = allocation_service.allocate_resource_to_mission(
        mission_id, "resource-food-ny-01", 100
    )
    second = allocation_service.allocate_resource_to_mission(
        mission_id, "resource-water-la-01", 200
    )

    response = client.get(f"/mission/{mission_id}/allocations")

    assert response.status_code == 200
    assert [item["allocation_id"] for item in response.json()] == [
        first.allocation_id,
        second.allocation_id,
    ]


def test_get_mission_allocations_returns_empty_list_when_none_exist() -> None:
    create_response = client.post("/mission", json=_valid_payload())
    mission_id = create_response.json()["mission_id"]

    response = client.get(f"/mission/{mission_id}/allocations")

    assert response.status_code == 200
    assert response.json() == []


def test_get_mission_allocations_unknown_mission_returns_http_404() -> None:
    response = client.get("/mission/unknown-mission-id/allocations")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_get_mission_allocations_response_contains_complete_record() -> None:
    create_response = client.post("/mission", json=_valid_payload())
    mission_id = create_response.json()["mission_id"]
    allocation_service.allocate_resource_to_mission(
        mission_id, "resource-food-ny-01", 100
    )

    response = client.get(f"/mission/{mission_id}/allocations")

    assert response.status_code == 200
    assert set(response.json()[0]) == {
        "allocation_id",
        "resource_id",
        "quantity",
        "mission_id",
        "disaster_id",
        "allocated_at",
        "status",
    }


def test_patch_mission_assigned_to_deployed_returns_http_200() -> None:
    create_response = client.post("/mission", json=_valid_payload())
    mission_id = create_response.json()["mission_id"]

    response = client.patch(f"/mission/{mission_id}/status", json={"status": "DEPLOYED"})

    assert response.status_code == 200
    assert response.json()["status"] == "DEPLOYED"


def test_patch_mission_valid_lifecycle_transitions_are_supported() -> None:
    create_response = client.post("/mission", json=_valid_payload())
    mission_id = create_response.json()["mission_id"]

    for next_status in ("DEPLOYED", "EN_ROUTE", "ARRIVED", "COMPLETED"):
        response = client.patch(f"/mission/{mission_id}/status", json={"status": next_status})
        assert response.status_code == 200
        assert response.json()["status"] == next_status


def test_patch_mission_response_contains_updated_status() -> None:
    create_response = client.post("/mission", json=_valid_payload())
    mission_id = create_response.json()["mission_id"]

    response = client.patch(f"/mission/{mission_id}/status", json={"status": "DEPLOYED"})

    assert response.status_code == 200
    assert response.json()["status"] == "DEPLOYED"


def test_patch_mission_unknown_id_returns_http_404() -> None:
    response = client.patch("/mission/does-not-exist/status", json={"status": "DEPLOYED"})
    assert response.status_code == 404
    assert "detail" in response.json()


def test_patch_mission_invalid_lifecycle_transition_returns_http_400() -> None:
    create_response = client.post("/mission", json=_valid_payload())
    mission_id = create_response.json()["mission_id"]

    response = client.patch(f"/mission/{mission_id}/status", json={"status": "COMPLETED"})

    assert response.status_code == 400
    assert "detail" in response.json()
    assert "Invalid mission status transition" in response.json()["detail"]


@pytest.mark.parametrize(
    "prior_statuses",
    [
        (),
        ("DEPLOYED",),
        ("DEPLOYED", "EN_ROUTE"),
        ("DEPLOYED", "EN_ROUTE", "ARRIVED"),
    ],
)
def test_patch_mission_can_cancel_from_any_active_status(
    prior_statuses: tuple[str, ...],
) -> None:
    create_response = client.post("/mission", json=_valid_payload())
    mission_id = create_response.json()["mission_id"]
    for status_value in prior_statuses:
        transition_response = client.patch(
            f"/mission/{mission_id}/status",
            json={"status": status_value},
        )
        assert transition_response.status_code == 200
        assert transition_response.json()["status"] == status_value

    response = client.patch(
        f"/mission/{mission_id}/status",
        json={"status": "CANCELLED"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    team = next(
        team for team in rescue_team_service._RESCUE_TEAMS
        if team.team_id == response.json()["team_id"]
    )
    assert team.availability == rescue_team_service.Availability.AVAILABLE
    assert team.current_mission_id is None


@pytest.mark.parametrize(
    ("terminal_status", "attempted_status"),
    [
        ("COMPLETED", "CANCELLED"),
        ("COMPLETED", "COMPLETED"),
        ("CANCELLED", "ASSIGNED"),
        ("CANCELLED", "DEPLOYED"),
    ],
)
def test_patch_mission_rejects_changes_to_terminal_missions(
    terminal_status: str,
    attempted_status: str,
) -> None:
    create_response = client.post("/mission", json=_valid_payload())
    mission_id = create_response.json()["mission_id"]
    if terminal_status == "COMPLETED":
        for status_value in ("DEPLOYED", "EN_ROUTE", "ARRIVED"):
            transition_response = client.patch(
                f"/mission/{mission_id}/status",
                json={"status": status_value},
            )
            assert transition_response.status_code == 200

    terminal_response = client.patch(
        f"/mission/{mission_id}/status",
        json={"status": terminal_status},
    )
    assert terminal_response.status_code == 200

    response = client.patch(
        f"/mission/{mission_id}/status",
        json={"status": attempted_status},
    )

    assert response.status_code == 400
    assert "Invalid mission status transition" in response.json()["detail"]
    assert mission_service.get_mission(mission_id).status.value == terminal_status


def test_patch_mission_invalid_status_value_returns_http_422() -> None:
    create_response = client.post("/mission", json=_valid_payload())
    mission_id = create_response.json()["mission_id"]

    response = client.patch(f"/mission/{mission_id}/status", json={"status": "NOT_A_REAL_STATE"})
    assert response.status_code == 422


def test_patch_mission_missing_status_returns_http_422() -> None:
    create_response = client.post("/mission", json=_valid_payload())
    mission_id = create_response.json()["mission_id"]

    response = client.patch(f"/mission/{mission_id}/status", json={})
    assert response.status_code == 422


def test_patch_mission_preserves_other_fields() -> None:
    create_response = client.post(
        "/mission",
        json=_valid_payload(hospital_id="hospital-88", vehicle_id="vehicle-88"),
    )
    created = create_response.json()
    mission_id = created["mission_id"]

    response = client.patch(f"/mission/{mission_id}/status", json={"status": "DEPLOYED"})
    updated = response.json()

    assert response.status_code == 200
    assert updated["mission_id"] == created["mission_id"]
    assert updated["disaster_id"] == created["disaster_id"]
    assert updated["team_id"] == created["team_id"]
    assert updated["hospital_id"] == created["hospital_id"]
    assert updated["vehicle_id"] == created["vehicle_id"]
    assert updated["destination_latitude"] == created["destination_latitude"]
    assert updated["destination_longitude"] == created["destination_longitude"]
    assert updated["priority"] == created["priority"]
    assert updated["created_at"] == created["created_at"]


def test_post_mission_returns_correct_http_201_status() -> None:
    response = client.post("/mission", json=_valid_payload())
    assert response.status_code == 201


def test_get_mission_returns_http_200_for_existing_mission() -> None:
    create_response = client.post("/mission", json=_valid_payload())
    mission_id = create_response.json()["mission_id"]

    response = client.get(f"/mission/{mission_id}")
    assert response.status_code == 200


def test_patch_mission_returns_http_200_for_valid_transition() -> None:
    create_response = client.post("/mission", json=_valid_payload())
    mission_id = create_response.json()["mission_id"]

    response = client.patch(f"/mission/{mission_id}/status", json={"status": "DEPLOYED"})
    assert response.status_code == 200


def test_error_responses_contain_detail_field() -> None:
    bad_team_response = client.post("/mission", json=_valid_payload(team_id="missing-team"))
    missing_mission_response = client.get("/mission/not-found")
    invalid_transition_response = client.post("/mission", json=_valid_payload())
    invalid_transition_response = client.patch(
        f"/mission/{invalid_transition_response.json()['mission_id']}/status",
        json={"status": "COMPLETED"},
    )

    assert bad_team_response.status_code == 400
    assert "detail" in bad_team_response.json()
    assert missing_mission_response.status_code == 404
    assert "detail" in missing_mission_response.json()
    assert invalid_transition_response.status_code == 400
    assert "detail" in invalid_transition_response.json()
