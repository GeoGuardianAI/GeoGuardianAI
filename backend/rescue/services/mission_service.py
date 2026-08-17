"""In-memory mission management for the Resource & Rescue Management module.

This service keeps mission state in memory for deterministic local testing and
business logic validation. It does not include database persistence or API code.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.rescue.models.mission import Mission, MissionPriority, MissionStatus
from backend.rescue.models.rescue_team import Availability, RescueTeam
from backend.rescue.services import rescue_team_service

_MISSIONS: dict[str, Mission] = {}
_NEXT_MISSION_NUMBER = 1

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
    """Create a mission and assign the supplied rescue team.

    The team must exist and be `AVAILABLE` before assignment. A new mission ID is
    generated deterministically in sequence, and the team's availability state is
    updated to reflect the created mission state.
    """
    team = _get_team(team_id)
    if team.availability != Availability.AVAILABLE:
        raise ValueError(f"Rescue team '{team_id}' is not available for assignment")

    resolved_status = _coerce_status(status)
    if resolved_status != MissionStatus.ASSIGNED:
        raise ValueError("Mission creation requires the initial status to be ASSIGNED")

    mission_id = _next_mission_id()
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

    _MISSIONS[mission_id] = mission
    team.current_mission_id = mission_id
    _set_team_availability(team_id, resolved_status)
    return mission


def get_mission(mission_id: str) -> Mission:
    """Return a mission by identifier."""
    try:
        return _MISSIONS[mission_id]
    except KeyError as exc:
        raise ValueError(f"Mission '{mission_id}' does not exist") from exc


def update_mission_status(
    mission_id: str,
    new_status: MissionStatus | str,
) -> Mission:
    """Update the status of an existing mission and synchronize team availability."""
    mission = get_mission(mission_id)
    resolved_status = _coerce_status(new_status)

    valid_next = _VALID_TRANSITIONS.get(mission.status, set())
    if resolved_status not in valid_next:
        valid_states = ", ".join(s.value for s in sorted(valid_next, key=lambda item: item.value))
        raise ValueError(
            f"Invalid mission status transition from {mission.status.value} to {resolved_status.value}. "
            f"Valid next states: {valid_states or 'none'}"
        )

    mission.status = resolved_status
    team = _get_team(mission.team_id)
    team.current_mission_id = mission_id if resolved_status not in {MissionStatus.COMPLETED, MissionStatus.CANCELLED} else None
    _set_team_availability(mission.team_id, resolved_status)
    return mission
