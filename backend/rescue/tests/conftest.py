import os

import pytest

os.environ["GEOGUARDIAN_DATABASE_PATH"] = ":memory:"


@pytest.fixture(autouse=True)
def synchronize_persisted_test_state():
    """Align SQLite with each test's established in-memory fixture baseline."""
    from backend.rescue.persistence import persist_state, transaction
    from backend.rescue.services import (
        allocation_service,
        detection_integration_service,
        emergency_resource_service,
        emergency_vehicle_service,
        mission_service,
        rescue_team_service,
        shelter_service,
    )

    def snapshot():
        return {
            "missions": [
                item.model_copy(deep=True)
                for item in mission_service._MISSIONS.values()
            ],
            "resources": [
                item.model_copy(deep=True)
                for item in emergency_resource_service._RESOURCES
            ],
            "allocations": [
                item.model_copy(deep=True)
                for item in allocation_service._ALLOCATIONS.values()
            ],
            "vehicles": [
                item.model_copy(deep=True)
                for item in emergency_vehicle_service._VEHICLES
            ],
            "rescue_teams": [
                item.model_copy(deep=True)
                for item in rescue_team_service._RESCUE_TEAMS
            ],
            "shelters": [
                item.model_copy(deep=True) for item in shelter_service._SHELTERS
            ],
            "emergency_shelters": [
                item.model_copy(deep=True)
                for item in shelter_service._EMERGENCY_SHELTERS
            ],
            "detection_links": [
                item.model_copy(deep=True)
                for item in detection_integration_service._DETECTION_MISSION_LINKS.values()
            ],
        }

    def write_snapshot(state):
        persist_state(state)
        with transaction() as connection:
            connection.execute("DELETE FROM operational_audit_events")

    def restore_cache(state):
        mission_service._MISSIONS.clear()
        mission_service._MISSIONS.update(
            (item.mission_id, item.model_copy(deep=True))
            for item in state["missions"]
        )
        allocation_service._ALLOCATIONS.clear()
        allocation_service._ALLOCATIONS.update(
            (item.allocation_id, item.model_copy(deep=True))
            for item in state["allocations"]
        )
        detection_integration_service._DETECTION_MISSION_LINKS.clear()
        detection_integration_service._DETECTION_MISSION_LINKS.update(
            (item.detection_id, item.model_copy(deep=True))
            for item in state["detection_links"]
        )
        emergency_resource_service._RESOURCES[:] = [
            item.model_copy(deep=True) for item in state["resources"]
        ]
        emergency_vehicle_service._VEHICLES[:] = [
            item.model_copy(deep=True) for item in state["vehicles"]
        ]
        rescue_team_service._RESCUE_TEAMS[:] = [
            item.model_copy(deep=True) for item in state["rescue_teams"]
        ]
        shelter_service._SHELTERS[:] = [
            item.model_copy(deep=True) for item in state["shelters"]
        ]
        shelter_service._EMERGENCY_SHELTERS[:] = [
            item.model_copy(deep=True) for item in state["emergency_shelters"]
        ]
        mission_service._NEXT_MISSION_NUMBER = max(
            (
                int(item.mission_id.removeprefix("mission-"))
                for item in state["missions"]
                if item.mission_id.startswith("mission-")
                and item.mission_id.removeprefix("mission-").isdigit()
            ),
            default=0,
        ) + 1
        allocation_service._NEXT_ALLOCATION_NUMBER = max(
            (
                int(item.allocation_id.removeprefix("allocation-"))
                for item in state["allocations"]
                if item.allocation_id.startswith("allocation-")
                and item.allocation_id.removeprefix("allocation-").isdigit()
            ),
            default=0,
        ) + 1

    initial_state = snapshot()
    restore_cache(initial_state)
    write_snapshot(initial_state)
    yield
    restore_cache(initial_state)
    write_snapshot(initial_state)
