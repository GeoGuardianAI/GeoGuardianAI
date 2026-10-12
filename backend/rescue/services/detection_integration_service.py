"""Safe operator-confirmed handoff from detector payloads to rescue missions."""

from __future__ import annotations

from pydantic import BaseModel

from backend.rescue.models.audit_event import AuditEventType
from backend.rescue.models.detection_integration import (
    DetectionMissionLink,
    DisasterDetectionAdapter,
)
from backend.rescue.models.mission import Mission, MissionPriority
from backend.rescue.persistence import (
    load_or_seed,
    load_records,
    persist_state,
    transaction,
)
from backend.rescue.services import mission_service
from backend.rescue.services.allocation_service import _MISSION_ALLOCATION_LOCK
from backend.rescue.services.audit_service import create_audit_event

_DETECTION_MISSION_LINKS: dict[str, DetectionMissionLink] = {
    link.detection_id: link
    for link in load_or_seed("detection_links", [], DetectionMissionLink)
}


class DuplicateDetectionError(ValueError):
    """Raised when an upstream detection has already created a mission."""


def create_mission_from_detection(
    detection: DisasterDetectionAdapter,
    *,
    team_id: str,
    priority: MissionPriority | str,
    confirmed: bool,
    hospital_id: str | None = None,
    vehicle_id: str | None = None,
) -> Mission:
    """Create an assigned mission from validated detection data after confirmation.

    The detection ID is durably unique. Mission, team assignment, and the
    detection-to-mission link are committed in one SQLite transaction.
    """
    if confirmed is not True:
        raise ValueError("Operator confirmation is required before mission creation")

    with _MISSION_ALLOCATION_LOCK:
        prior_missions = dict(mission_service._MISSIONS)
        prior_next_number = mission_service._NEXT_MISSION_NUMBER
        team = mission_service._get_team(team_id)
        prior_team_availability = team.availability
        prior_team_mission_id = team.current_mission_id
        link: DetectionMissionLink | None = None
        try:
            with transaction() as connection:
                persisted_links = load_records(
                    connection, "detection_links", DetectionMissionLink
                )
                existing_link = next(
                    (
                        item
                        for item in persisted_links
                        if item.detection_id == detection.detection_id
                    ),
                    None,
                )
                if existing_link is not None:
                    raise DuplicateDetectionError(
                        f"Detection '{detection.detection_id}' is already linked to "
                        f"mission '{existing_link.mission_id}'"
                    )
                mission = mission_service.create_mission(
                    team_id=team_id,
                    disaster_id=detection.disaster_id,
                    destination_latitude=detection.latitude,
                    destination_longitude=detection.longitude,
                    priority=priority,
                    hospital_id=hospital_id,
                    vehicle_id=vehicle_id,
                )
                link = DetectionMissionLink(
                    detection_id=detection.detection_id,
                    mission_id=mission.mission_id,
                    detection=detection,
                )
                links = [*persisted_links, link]
                persist_state(
                    {
                        "detection_links": links,
                    },
                    audit_events=[
                        create_audit_event(
                            AuditEventType.DETECTION_MISSION_LINKED,
                            mission_id=mission.mission_id,
                            disaster_id=detection.disaster_id,
                            detection_id=detection.detection_id,
                            summary={
                                "operator_confirmed": True,
                                "mission_status": mission.status.value,
                                "coordinates_used": True,
                                "severity_supplied": detection.severity is not None,
                                "confidence_supplied": detection.confidence is not None,
                                "affected_population_supplied": detection.affected_population is not None,
                            },
                        )
                    ],
                )
        except Exception:
            mission_service._MISSIONS.clear()
            mission_service._MISSIONS.update(prior_missions)
            mission_service._NEXT_MISSION_NUMBER = prior_next_number
            team.availability = prior_team_availability
            team.current_mission_id = prior_team_mission_id
            raise

        if link is None:
            raise RuntimeError("Detection mission transaction completed without a link")
        _DETECTION_MISSION_LINKS.clear()
        _DETECTION_MISSION_LINKS.update(
            (item.detection_id, item) for item in links
        )
        _DETECTION_MISSION_LINKS[detection.detection_id] = link
        return mission


def get_detection_mission_link(detection_id: str) -> DetectionMissionLink | None:
    """Return the durable local association, if this detection was used."""
    return _DETECTION_MISSION_LINKS.get(detection_id)
