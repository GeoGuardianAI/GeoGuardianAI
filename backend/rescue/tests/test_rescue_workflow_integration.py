"""Isolated end-to-end verification of the rescue-management API workflow."""

import os
from pathlib import Path
import subprocess
import sys
import textwrap


def _run_isolated_scenario(database_path: Path, scenario: str) -> None:
    project_root = Path(__file__).resolve().parents[3]
    environment = os.environ.copy()
    environment["GEOGUARDIAN_DATABASE_PATH"] = str(database_path)
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(scenario)],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_confirmed_detection_to_completed_mission_workflow(tmp_path: Path) -> None:
    _run_isolated_scenario(
        tmp_path / "complete-workflow.sqlite3",
        """
        from fastapi.testclient import TestClient

        from backend.rescue.main import app

        client = TestClient(app)
        detection = {
            "detection_id": "integration-detection-complete-001",
            "disaster_id": "integration-flood-001",
            "disaster_type": "flood",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "severity": 4,
            "confidence": 0.91,
            "affected_population": 750,
            "critical_infrastructure": True,
        }
        response = client.post(
            "/mission/from-detection",
            json={
                "detection": detection,
                "team_id": "rescue-ny-01",
                "priority": "HIGH",
                "confirmed": True,
            },
        )
        assert response.status_code == 201, response.text
        mission = response.json()
        mission_id = mission["mission_id"]
        assert mission["status"] == "ASSIGNED"
        assert mission["disaster_id"] == detection["disaster_id"]
        assert mission["destination_latitude"] == detection["latitude"]
        assert mission["destination_longitude"] == detection["longitude"]

        listed = client.get("/missions")
        assert listed.status_code == 200
        assert any(item["mission_id"] == mission_id for item in listed.json())

        risk_response = client.post(
            "/risk-priority",
            json={
                key: detection[key]
                for key in (
                    "disaster_id",
                    "disaster_type",
                    "latitude",
                    "longitude",
                    "severity",
                    "affected_population",
                    "critical_infrastructure",
                )
            },
        )
        assert risk_response.status_code == 200, risk_response.text
        expected_score = risk_response.json()["risk_score"]
        ranked = client.get("/missions/ranked")
        assert ranked.status_code == 200
        ranked_mission = next(
            entry for entry in ranked.json()["missions"]
            if entry["mission"]["mission_id"] == mission_id
        )
        assert ranked_mission["disaster_risk_score"] == expected_score

        requirement = {
            "mission_id": mission_id,
            "requirements": [{"resource_type": "FOOD", "quantity": 20}],
        }
        readiness = client.post(
            "/assess-resource-readiness-for-mission", json=requirement
        )
        assert readiness.status_code == 200, readiness.text
        readiness_data = readiness.json()
        assert readiness_data["ready"] is True
        assert readiness_data["assessment_only"] is True
        assert readiness_data["requirements"][0]["mission_allocated_quantity"] == 0
        assert readiness_data["requirements"][0]["inventory_available_quantity"] >= 20

        recommendation = client.post(
            "/recommend-resources-for-mission",
            json={
                "mission_id": mission_id,
                "resource_type": "FOOD",
                "quantity": 20,
            },
        )
        assert recommendation.status_code == 200, recommendation.text
        recommendation_data = recommendation.json()
        assert recommendation_data["mission_id"] == mission_id
        assert recommendation_data["disaster_id"] == detection["disaster_id"]
        assert recommendation_data["recommendation_only"] is True
        resource_id = recommendation_data["recommended_resources"][0]["resource_id"]
        before = client.get("/available-resources").json()
        quantity_before = next(
            item["available_quantity"]
            for item in before
            if item["resource_id"] == resource_id
        )

        allocated = client.post(
            "/allocate-resource-to-mission",
            json={
                "mission_id": mission_id,
                "resource_id": resource_id,
                "quantity": 20,
            },
        )
        assert allocated.status_code == 200, allocated.text
        allocation = allocated.json()
        allocation_id = allocation["allocation_id"]
        assert allocation["status"] == "ALLOCATED"
        inventory_after_allocation = client.get("/available-resources").json()
        assert next(
            item["available_quantity"]
            for item in inventory_after_allocation
            if item["resource_id"] == resource_id
        ) == quantity_before - 20
        history = client.get(f"/mission/{mission_id}/allocations")
        assert history.status_code == 200
        assert any(item["allocation_id"] == allocation_id for item in history.json())

        for status in ("DEPLOYED", "EN_ROUTE", "ARRIVED", "COMPLETED"):
            changed = client.patch(
                f"/mission/{mission_id}/status", json={"status": status}
            )
            assert changed.status_code == 200, changed.text
            assert changed.json()["status"] == status

        completed_inventory = client.get("/available-resources").json()
        assert next(
            item["available_quantity"]
            for item in completed_inventory
            if item["resource_id"] == resource_id
        ) == quantity_before
        final_history = client.get(f"/mission/{mission_id}/allocations").json()
        assert len(final_history) == 1
        assert final_history[0]["allocation_id"] == allocation_id
        assert final_history[0]["status"] == "RELEASED"
        team_list = client.get(
            "/available-team",
            params={
                "latitude": detection["latitude"],
                "longitude": detection["longitude"],
            },
        )
        assert team_list.status_code == 200
        completed_team = next(
            team for team in team_list.json()
            if team["team_id"] == mission["team_id"]
        )
        assert completed_team["availability"] == "AVAILABLE"
        assert completed_team["current_mission_id"] is None

        audit = client.get("/audit-events", params={"mission_id": mission_id})
        assert audit.status_code == 200
        audit_types = {item["event_type"] for item in audit.json()["items"]}
        assert {
            "MISSION_CREATED",
            "DETECTION_MISSION_LINKED",
            "RESOURCE_ALLOCATED",
            "MISSION_STATUS_CHANGED",
            "RESOURCE_SETTLED_RELEASED",
        } <= audit_types
        assert sum(
            item["event_type"] == "RESOURCE_SETTLED_RELEASED"
            and item["summary"]["allocation_id"] == allocation_id
            for item in audit.json()["items"]
        ) == 1
        """,
    )


def test_cancelled_mission_cancels_allocation_without_restoring_inventory(
    tmp_path: Path,
) -> None:
    _run_isolated_scenario(
        tmp_path / "cancel-workflow.sqlite3",
        """
        from fastapi.testclient import TestClient

        from backend.rescue.main import app

        client = TestClient(app)
        created = client.post(
            "/mission/from-detection",
            json={
                "detection": {
                    "detection_id": "integration-detection-cancel-001",
                    "disaster_id": "integration-fire-001",
                    "disaster_type": "fire",
                    "latitude": 12.9716,
                    "longitude": 77.5946,
                },
                "team_id": "rescue-ny-01",
                "priority": "CRITICAL",
                "confirmed": True,
            },
        )
        assert created.status_code == 201, created.text
        mission_id = created.json()["mission_id"]
        recommendation = client.post(
            "/recommend-resources-for-mission",
            json={"mission_id": mission_id, "resource_type": "WATER", "quantity": 1},
        )
        assert recommendation.status_code == 200, recommendation.text
        resource_id = recommendation.json()["recommended_resources"][0]["resource_id"]
        quantity_before = next(
            item["available_quantity"]
            for item in client.get("/available-resources").json()
            if item["resource_id"] == resource_id
        )
        allocated = client.post(
            "/allocate-resource-to-mission",
            json={
                "mission_id": mission_id,
                "resource_id": resource_id,
                "quantity": 15,
            },
        )
        assert allocated.status_code == 200, allocated.text
        allocation_id = allocated.json()["allocation_id"]
        cancelled = client.patch(
            f"/mission/{mission_id}/status", json={"status": "CANCELLED"}
        )
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "CANCELLED"

        current_quantity = next(
            item["available_quantity"]
            for item in client.get("/available-resources").json()
            if item["resource_id"] == resource_id
        )
        assert current_quantity == quantity_before - 15
        history = client.get(f"/mission/{mission_id}/allocations")
        assert history.status_code == 200
        assert history.json()[0]["allocation_id"] == allocation_id
        assert history.json()[0]["status"] == "CANCELLED"
        events = client.get(
            "/audit-events", params={"mission_id": mission_id}
        ).json()["items"]
        assert sum(
            item["event_type"] == "RESOURCE_SETTLED_CANCELLED"
            and item["summary"]["allocation_id"] == allocation_id
            and item["summary"]["inventory_restored"] is False
            for item in events
        ) == 1
        """,
    )


def test_failed_validation_and_operations_leave_workflow_state_unchanged(
    tmp_path: Path,
) -> None:
    _run_isolated_scenario(
        tmp_path / "failed-operations.sqlite3",
        """
        from fastapi.testclient import TestClient

        from backend.rescue.main import app

        client = TestClient(app)
        payload = {
            "detection": {
                "detection_id": "integration-detection-failure-001",
                "disaster_id": "integration-storm-001",
                "disaster_type": "storm",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
            "team_id": "rescue-ny-01",
            "priority": "HIGH",
            "confirmed": True,
        }
        before_missions = client.get("/missions").json()
        before_inventory = client.get("/available-resources").json()
        before_events = client.get("/audit-events").json()
        unconfirmed = {**payload, "confirmed": False}
        rejected = client.post("/mission/from-detection", json=unconfirmed)
        assert rejected.status_code == 400
        invalid_coordinates = {
            **payload,
            "detection": {**payload["detection"], "latitude": 91},
        }
        invalid = client.post("/mission/from-detection", json=invalid_coordinates)
        assert invalid.status_code == 422
        assert client.get("/missions").json() == before_missions
        assert client.get("/available-resources").json() == before_inventory
        assert client.get("/audit-events").json() == before_events

        created = client.post("/mission/from-detection", json=payload)
        assert created.status_code == 201, created.text
        mission_id = created.json()["mission_id"]
        mission_inventory = client.get("/available-resources").json()
        mission_events = client.get(
            "/audit-events", params={"mission_id": mission_id}
        ).json()
        mission_allocations = client.get(
            f"/mission/{mission_id}/allocations"
        ).json()

        invalid_transition = client.patch(
            f"/mission/{mission_id}/status", json={"status": "COMPLETED"}
        )
        assert invalid_transition.status_code == 400
        overspend = client.post(
            "/allocate-resource-to-mission",
            json={
                "mission_id": mission_id,
                "resource_id": "resource-food-ny-01",
                "quantity": 999999999,
            },
        )
        assert overspend.status_code == 400
        assert client.get(f"/mission/{mission_id}").json()["status"] == "ASSIGNED"
        assert client.get("/available-resources").json() == mission_inventory
        assert client.get(f"/mission/{mission_id}/allocations").json() == mission_allocations
        assert client.get(
            "/audit-events", params={"mission_id": mission_id}
        ).json() == mission_events
        """,
    )
