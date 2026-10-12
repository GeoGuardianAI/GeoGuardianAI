"""Mission management for the Resource & Rescue Management module.

The service retains its in-memory registry interface while persisting operational
state in the configured SQLite database.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.rescue.persistence import (
    load_or_seed,
    load_records,
    next_record_id,
    persist_state,
    transaction,
)
from backend.rescue.models.audit_event import AuditEventType
from backend.rescue.models.mission import Mission, MissionPriority, MissionStatus
from backend.rescue.models.rescue_team import Availability, RescueTeam
from backend.rescue.services.audit_service import create_audit_event
from backend.rescue.services import rescue_team_service

_MISSIONS: dict[str, Mission] = {
    mission.mission_id: mission
    for mission in load_or_seed("missions", [], Mission)
}
_NEXT_MISSION_NUMBER = max(
    (
        int(mission_id.removeprefix("mission-"))
        for mission_id in _MISSIONS
        if mission_id.startswith("mission-")
        and mission_id.removeprefix("mission-").isdigit()
    ),
    default=0,
) + 1

_VALID_TRANSITIONS: dict[MissionStatus, set[MissionStatus]] = {
    MissionStatus.ASSIGNED: {MissionStatus.DEPLOYED, MissionStatus.CANCELLED},
    MissionStatus.DEPLOYED: {MissionStatus.EN_ROUTE, MissionStatus.CANCELLED},
    MissionStatus.EN_ROUTE: {MissionStatus.ARRIVED, MissionStatus.CANCELLED},
    MissionStatus.ARRIVED: {MissionStatus.COMPLETED, MissionStatus.CANCELLED},
    MissionStatus.COMPLETED: set(),
    MissionStatus.CANCELLED: set(),
}


def _next_mission_id() -> str:
    """Generate a deterministic mission ID in a simple incrementing sequence."""
    global _NEXT_MISSION_NUMBER
    mission_id = f"mission-{_NEXT_MISSION_NUMBER:04d}"
    _NEXT_MISSION_NUMBER += 1
    return mission_id


def _get_team(team_id: str) -> RescueTeam:
    """Return the in-memory rescue team matching the provided identifier."""
    for team in rescue_team_service._RESCUE_TEAMS:
        if team.team_id == team_id:
            return team
    raise ValueError(f"Rescue team '{team_id}' does not exist")


def _set_team_availability(team_id: str, mission_status: MissionStatus) -> None:
    """Update a team's availability to reflect the current mission state."""
    team = _get_team(team_id)
    if mission_status in {MissionStatus.ASSIGNED}:
        team.availability = Availability.ASSIGNED
    elif mission_status in {MissionStatus.DEPLOYED, MissionStatus.EN_ROUTE, MissionStatus.ARRIVED}:
        team.availability = Availability.DEPLOYED
    elif mission_status in {MissionStatus.COMPLETED, MissionStatus.CANCELLED}:
        team.availability = Availability.AVAILABLE
        team.current_mission_id = None
    else:
        team.availability = Availability.AVAILABLE


def _coerce_status(value: MissionStatus | str) -> MissionStatus:
    """Normalize the mission status to a MissionStatus enum value."""
    if isinstance(value, MissionStatus):
        return value
    return MissionStatus(value)


def _coerce_priority(value: MissionPriority | str) -> MissionPriority:
    """Normalize the mission priority to a MissionPriority enum value."""
    if isinstance(value, MissionPriority):
        return value
    return MissionPriority(value)


def create_mission(
    team_id: str,
    disaster_id: str,
    destination_latitude: float,
    destination_longitude: float,
    priority: MissionPriority | str = MissionPriority.MEDIUM,
    hospital_id: str | None = None,
    vehicle_id: str | None = None,
    status: MissionStatus | str = MissionStatus.ASSIGNED,
) -> Mission:
    """Create a mission while serializing team assignment and ID allocation."""
    from backend.rescue.services import allocation_service

    with allocation_service._MISSION_ALLOCATION_LOCK:
        return _create_mission_locked(
            team_id=team_id,
            disaster_id=disaster_id,
            destination_latitude=destination_latitude,
            destination_longitude=destination_longitude,
            priority=priority,
            hospital_id=hospital_id,
            vehicle_id=vehicle_id,
            status=status,
        )


def _create_mission_locked(
    team_id: str,
    disaster_id: str,
    destination_latitude: float,
    destination_longitude: float,
    priority: MissionPriority | str = MissionPriority.MEDIUM,
    hospital_id: str | None = None,
    vehicle_id: str | None = None,
    status: MissionStatus | str = MissionStatus.ASSIGNED,
) -> Mission:
    """Create a mission and assign the supplied rescue team.

    The team must exist and be `AVAILABLE` before assignment. A new mission ID is
    generated deterministically in sequence, and the team's availability state is
    updated to reflect the created mission state.
    """
    resolved_status = _coerce_status(status)
    if resolved_status != MissionStatus.ASSIGNED:
        raise ValueError("Mission creation requires the initial status to be ASSIGNED")

    global _NEXT_MISSION_NUMBER
    with transaction() as connection:
        missions = load_records(connection, "missions", Mission)
        teams = load_records(connection, "rescue_teams", RescueTeam)
        team = next((item for item in teams if item.team_id == team_id), None)
        if team is None:
            raise ValueError(f"Rescue team '{team_id}' does not exist")
        if team.availability != Availability.AVAILABLE:
            raise ValueError(f"Rescue team '{team_id}' is not available for assignment")
        mission_id = next_record_id(connection, "missions", "mission-")
        mission = Mission(
            mission_id=mission_id,
            disaster_id=disaster_id,
            team_id=team_id,
            hospital_id=hospital_id,
            vehicle_id=vehicle_id,
            destination_latitude=destination_latitude,
            destination_longitude=destination_longitude,
            priority=_coerce_priority(priority),
            status=resolved_status,
            created_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        )
        team.current_mission_id = mission_id
        team.availability = Availability.ASSIGNED
        missions.append(mission)
        persist_state(
            {
                "missions": missions,
                "rescue_teams": teams,
            },
            audit_events=[
                create_audit_event(
                    AuditEventType.MISSION_CREATED,
                    mission_id=mission.mission_id,
                    disaster_id=mission.disaster_id,
                    summary={
                        "team_id": mission.team_id,
                        "priority": mission.priority.value,
                        "status": mission.status.value,
                    },
                )
            ],
        )
    _replace_mission_cache(missions)
    _replace_team_cache(teams)
    _NEXT_MISSION_NUMBER = max(
        (
            int(item.mission_id.removeprefix("mission-"))
            for item in missions
            if item.mission_id.startswith("mission-")
            and item.mission_id.removeprefix("mission-").isdigit()
        ),
        default=0,
    ) + 1
    mission = _MISSIONS[mission_id]
    return mission


def _refresh_model_cache(existing: list, updated: list, key_name: str) -> list:
    current = {getattr(item, key_name): item for item in existing}
    result = []
    for item in updated:
        cached = current.get(getattr(item, key_name))
        if cached is None:
            result.append(item)
            continue
        for field_name, value in item:
            setattr(cached, field_name, value)
        result.append(cached)
    return result


def _replace_mission_cache(missions: list[Mission]) -> None:
    refreshed = _refresh_model_cache(list(_MISSIONS.values()), missions, "mission_id")
    _MISSIONS.clear()
    _MISSIONS.update((mission.mission_id, mission) for mission in refreshed)


def _replace_team_cache(teams: list[RescueTeam]) -> None:
    refreshed = _refresh_model_cache(
        rescue_team_service._RESCUE_TEAMS, teams, "team_id"
    )
    rescue_team_service._RESCUE_TEAMS[:] = refreshed


def get_mission(mission_id: str) -> Mission:
    """Return a mission by identifier."""
    try:
        return _MISSIONS[mission_id]
    except KeyError as exc:
        raise ValueError(f"Mission '{mission_id}' does not exist") from exc


def list_missions() -> list[Mission]:
    """Return all stored missions in insertion order."""
    return list(_MISSIONS.values())


def update_mission_status(
    mission_id: str,
    new_status: MissionStatus | str,
) -> Mission:
    """Update mission status, settle terminal allocations, and synchronize team availability.

    Completing a mission releases its active allocations and restores inventory.
    Cancelling a mission cancels its active allocations without restoring inventory.
    """
    from backend.rescue.services import allocation_service

    with allocation_service._MISSION_ALLOCATION_LOCK:
        with transaction() as connection:
            missions = load_records(connection, "missions", Mission)
            mission = next(
                (item for item in missions if item.mission_id == mission_id), None
            )
            if mission is None:
                raise ValueError(f"Mission '{mission_id}' does not exist")
            resolved_status = _coerce_status(new_status)
            valid_next = _VALID_TRANSITIONS.get(mission.status, set())
            if resolved_status not in valid_next:
                valid_states = ", ".join(
                    s.value for s in sorted(valid_next, key=lambda item: item.value)
                )
                raise ValueError(
                    f"Invalid mission status transition from {mission.status.value} to {resolved_status.value}. "
                    f"Valid next states: {valid_states or 'none'}"
                )

            teams = load_records(connection, "rescue_teams", RescueTeam)
            team = next(
                (item for item in teams if item.team_id == mission.team_id), None
            )
            if team is None:
                raise ValueError(f"Rescue team '{mission.team_id}' does not exist")
            allocations = load_records(
                connection, "allocations", allocation_service.ResourceAllocation
            )
            resources = load_records(
                connection,
                "resources",
                allocation_service.emergency_resource_service.EmergencyResource,
            )
            active_allocations = [
                item
                for item in allocations
                if item.mission_id == mission_id
                and item.status == allocation_service.ResourceAllocationStatus.ALLOCATED
            ]
            resource_by_id = {item.resource_id: item for item in resources}
            if resolved_status == MissionStatus.COMPLETED:
                for allocation in active_allocations:
                    resource = resource_by_id.get(allocation.resource_id)
                    if resource is None:
                        raise ValueError(
                            f"Resource '{allocation.resource_id}' does not exist"
                        )
                    resource.available_quantity += allocation.quantity
                    allocation.status = (
                        allocation_service.ResourceAllocationStatus.RELEASED
                    )
            elif resolved_status == MissionStatus.CANCELLED:
                for allocation in active_allocations:
                    allocation.status = (
                        allocation_service.ResourceAllocationStatus.CANCELLED
                    )

            previous_status = mission.status
            mission.status = resolved_status
            team.current_mission_id = (
                mission_id
                if resolved_status
                not in {MissionStatus.COMPLETED, MissionStatus.CANCELLED}
                else None
            )
            if resolved_status == MissionStatus.ASSIGNED:
                team.availability = Availability.ASSIGNED
            elif resolved_status in {
                MissionStatus.DEPLOYED,
                MissionStatus.EN_ROUTE,
                MissionStatus.ARRIVED,
            }:
                team.availability = Availability.DEPLOYED
            else:
                team.availability = Availability.AVAILABLE

            audit_events = [
                create_audit_event(
                    AuditEventType.MISSION_STATUS_CHANGED,
                    mission_id=mission.mission_id,
                    disaster_id=mission.disaster_id,
                    summary={
                        "from_status": previous_status.value,
                        "to_status": resolved_status.value,
                    },
                )
            ]
            if resolved_status in {MissionStatus.COMPLETED, MissionStatus.CANCELLED}:
                settlement_type = (
                    AuditEventType.RESOURCE_SETTLED_RELEASED
                    if resolved_status == MissionStatus.COMPLETED
                    else AuditEventType.RESOURCE_SETTLED_CANCELLED
                )
                for allocation in active_allocations:
                    audit_events.append(
                        create_audit_event(
                            settlement_type,
                            mission_id=mission.mission_id,
                            disaster_id=mission.disaster_id,
                            resource_id=allocation.resource_id,
                            summary={
                                "allocation_id": allocation.allocation_id,
                                "quantity": allocation.quantity,
                                "mission_terminal_status": resolved_status.value,
                                "inventory_restored": resolved_status
                                == MissionStatus.COMPLETED,
                            },
                        )
                    )
            persist_state(
                {
                    "missions": missions,
                    "rescue_teams": teams,
                    "allocations": allocations,
                    "resources": resources,
                },
                audit_events=audit_events,
            )
        _replace_mission_cache(missions)
        _replace_team_cache(teams)
        allocation_service._replace_allocation_cache(allocations)
        allocation_service.emergency_resource_service._replace_resource_cache(
            resources
        )
        return _MISSIONS[mission_id]
