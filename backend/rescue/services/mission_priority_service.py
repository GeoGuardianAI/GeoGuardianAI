"""Deterministic ranking of rescue missions using available risk and mission data."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Mapping, Sequence

from backend.rescue.models.mission import Mission, MissionPriority, MissionStatus
from backend.rescue.models.mission_ranking import MissionRankingResponse, RankedMission
from backend.rescue.services.mission_service import list_missions
from backend.rescue.services.risk_priority_service import get_risk_priority_scores

_PRIORITY_ORDER = {
    MissionPriority.CRITICAL: 0,
    MissionPriority.HIGH: 1,
    MissionPriority.MEDIUM: 2,
    MissionPriority.LOW: 3,
}
_STATUS_ORDER = {
    MissionStatus.ASSIGNED: 0,
    MissionStatus.DEPLOYED: 1,
    MissionStatus.EN_ROUTE: 2,
    MissionStatus.ARRIVED: 3,
    MissionStatus.COMPLETED: 4,
    MissionStatus.CANCELLED: 5,
}
_RISK_RANKING_BASIS = (
    "known disaster risk score descending (known scores before unassessed), "
    "manual mission priority descending, active status before terminal status "
    "in lifecycle order, creation time oldest first, mission ID ascending"
)
_NO_RISK_RANKING_BASIS = (
    "manual mission priority descending, active status before terminal status "
    "in lifecycle order, creation time oldest first, mission ID ascending; "
    "disaster risk unassessed"
)


def _created_at_order(value: str) -> datetime:
    """Parse ISO-8601 mission creation time; interpret naive values as UTC."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"Mission creation time '{value}' is not valid ISO-8601") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _validated_risk_scores(
    missions: Sequence[Mission],
    disaster_risk_scores: Mapping[str, float] | None,
) -> dict[str, float]:
    if disaster_risk_scores is None:
        return {}

    mission_disaster_ids = {mission.disaster_id for mission in missions}
    resolved_scores: dict[str, float] = {}
    if not isinstance(disaster_risk_scores, Mapping):
        raise ValueError("Disaster risk scores must be a mapping of disaster IDs to scores")

    for disaster_id, score in disaster_risk_scores.items():
        if not isinstance(disaster_id, str) or not disaster_id.strip():
            raise ValueError("Risk score disaster identifiers must not be empty")
        if disaster_id not in mission_disaster_ids:
            raise ValueError(f"Risk score references unknown disaster '{disaster_id}'")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise ValueError(
                f"Risk score for disaster '{disaster_id}' must be between 0 and 100"
            )
        try:
            numeric_score = float(score)
        except OverflowError as exc:
            raise ValueError(
                f"Risk score for disaster '{disaster_id}' must be between 0 and 100"
            ) from exc
        if not math.isfinite(numeric_score) or not 0.0 <= numeric_score <= 100.0:
            raise ValueError(
                f"Risk score for disaster '{disaster_id}' must be between 0 and 100"
            )
        resolved_scores[disaster_id] = numeric_score
    return resolved_scores


def rank_missions(
    missions: Sequence[Mission] | None = None,
    disaster_risk_scores: Mapping[str, float] | None = None,
) -> MissionRankingResponse:
    """Rank missions using only supplied, validated disaster risk and mission data.

    Known risk scores sort before unassessed missions, with higher scores first.
    When no score mapping is supplied, use previously calculated scores cached
    by the risk-priority service; ranking never triggers recalculation.
    Manual priority, lifecycle status, oldest creation time, and mission ID then
    provide deterministic tie-breaks. If no risk scores exist, ranking uses
    mission priority, status, creation time, and mission ID.
    """
    mission_records = list(list_missions() if missions is None else missions)
    mission_ids = [mission.mission_id for mission in mission_records]
    if len(mission_ids) != len(set(mission_ids)):
        raise ValueError("Mission identifiers must be unique for ranking")

    if disaster_risk_scores is None:
        disaster_risk_scores = get_risk_priority_scores(
            {mission.disaster_id for mission in mission_records}
        )
    risk_scores = _validated_risk_scores(mission_records, disaster_risk_scores)
    ordered = sorted(
        mission_records,
        key=lambda mission: (
            0 if mission.disaster_id in risk_scores else 1,
            -risk_scores.get(mission.disaster_id, 0.0),
            _PRIORITY_ORDER[mission.priority],
            _STATUS_ORDER[mission.status],
            _created_at_order(mission.created_at),
            mission.mission_id,
        ),
    )
    missing_risk_disaster_ids = sorted(
        {mission.disaster_id for mission in mission_records if mission.disaster_id not in risk_scores}
    )
    has_risk_data = any(mission.disaster_id in risk_scores for mission in mission_records)

    return MissionRankingResponse(
        risk_data_available=has_risk_data,
        missing_risk_disaster_ids=missing_risk_disaster_ids,
        ranking_basis=_RISK_RANKING_BASIS if has_risk_data else _NO_RISK_RANKING_BASIS,
        missions=[
            RankedMission(
                rank=rank,
                mission=mission,
                disaster_risk_score=risk_scores.get(mission.disaster_id),
            )
            for rank, mission in enumerate(ordered, start=1)
        ],
    )
