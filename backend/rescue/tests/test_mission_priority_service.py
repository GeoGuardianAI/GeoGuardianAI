"""Tests for deterministic, disaster-aware mission ranking."""

from __future__ import annotations

import pytest

from backend.rescue.models.mission import Mission, MissionPriority, MissionStatus
from backend.rescue.models.risk_priority import RiskPriorityRequest
from backend.rescue.services.mission_priority_service import rank_missions
from backend.rescue.services import risk_priority_service
from backend.rescue.services.risk_priority_service import (
    _RISK_PRIORITY_RESULTS,
    calculate_risk_priority,
)


@pytest.fixture(autouse=True)
def reset_risk_priority_results():
    original_results = _RISK_PRIORITY_RESULTS.copy()
    _RISK_PRIORITY_RESULTS.clear()
    yield
    _RISK_PRIORITY_RESULTS.clear()
    _RISK_PRIORITY_RESULTS.update(original_results)


def _mission(
    mission_id: str,
    *,
    disaster_id: str = "disaster-001",
    priority: MissionPriority = MissionPriority.MEDIUM,
    status: MissionStatus = MissionStatus.ASSIGNED,
    created_at: str = "2026-01-01T00:00:00+00:00",
) -> Mission:
    return Mission(
        mission_id=mission_id,
        disaster_id=disaster_id,
        team_id=f"team-{mission_id}",
        destination_latitude=12.0,
        destination_longitude=77.0,
        priority=priority,
        status=status,
        created_at=created_at,
    )


def test_risk_scores_rank_disasters_before_manual_priority() -> None:
    lower_risk_critical_manual_priority = _mission(
        "mission-1",
        disaster_id="disaster-low",
        priority=MissionPriority.CRITICAL,
    )
    higher_risk_low_manual_priority = _mission(
        "mission-2",
        disaster_id="disaster-high",
        priority=MissionPriority.LOW,
    )

    result = rank_missions(
        [lower_risk_critical_manual_priority, higher_risk_low_manual_priority],
        {"disaster-low": 25.0, "disaster-high": 80.0},
    )

    assert [entry.mission.mission_id for entry in result.missions] == [
        "mission-2",
        "mission-1",
    ]
    assert [entry.rank for entry in result.missions] == [1, 2]
    assert [entry.disaster_risk_score for entry in result.missions] == [80.0, 25.0]
    assert result.risk_data_available is True
    assert result.missing_risk_disaster_ids == []


def test_calculated_risk_is_associated_by_disaster_id_for_multiple_missions() -> None:
    calculate_risk_priority(
        RiskPriorityRequest(
            disaster_id="disaster-high-risk",
            disaster_type="flood",
            latitude=12.0,
            longitude=77.0,
            severity=5,
            affected_population=10000,
            critical_infrastructure=True,
        )
    )
    missions = [
        _mission("mission-other", disaster_id="disaster-no-risk"),
        _mission("mission-high-2", disaster_id="disaster-high-risk"),
        _mission("mission-high-1", disaster_id="disaster-high-risk"),
    ]

    result = rank_missions(missions)

    assert [entry.mission.mission_id for entry in result.missions] == [
        "mission-high-1",
        "mission-high-2",
        "mission-other",
    ]
    assert [entry.disaster_risk_score for entry in result.missions] == [
        100.0,
        100.0,
        None,
    ]
    assert result.missing_risk_disaster_ids == ["disaster-no-risk"]


def test_ranking_reuses_cached_calculation_without_recalculating(monkeypatch) -> None:
    calculate_risk_priority(
        RiskPriorityRequest(
            disaster_id="disaster-cached",
            disaster_type="flood",
            latitude=12.0,
            longitude=77.0,
            severity=3,
            affected_population=3333,
        )
    )

    def unexpected_recalculation(*args, **kwargs):
        pytest.fail("Mission ranking must use the cached score, not recalculate")

    monkeypatch.setattr(
        risk_priority_service,
        "calculate_risk_priority",
        unexpected_recalculation,
    )
    result = rank_missions([_mission("mission-cached", disaster_id="disaster-cached")])

    assert result.missions[0].disaster_risk_score == 35.0


def test_scored_missions_rank_before_unassessed_missions_without_fabricating_score() -> None:
    unassessed = _mission(
        "mission-unassessed",
        disaster_id="disaster-unassessed",
        priority=MissionPriority.CRITICAL,
    )
    assessed = _mission(
        "mission-assessed",
        disaster_id="disaster-assessed",
        priority=MissionPriority.LOW,
    )

    result = rank_missions([unassessed, assessed], {"disaster-assessed": 0.0})

    assert [entry.mission.mission_id for entry in result.missions] == [
        "mission-assessed",
        "mission-unassessed",
    ]
    assert result.missions[0].disaster_risk_score == 0.0
    assert result.missions[1].disaster_risk_score is None
    assert result.missing_risk_disaster_ids == ["disaster-unassessed"]


def test_missing_risk_data_uses_priority_status_oldest_time_and_id_tie_breakers() -> None:
    missions = [
        _mission(
            "mission-z",
            priority=MissionPriority.HIGH,
            status=MissionStatus.DEPLOYED,
            created_at="2026-01-02T00:00:00Z",
        ),
        _mission(
            "mission-b",
            priority=MissionPriority.HIGH,
            status=MissionStatus.ASSIGNED,
            created_at="2026-01-02T00:00:00+00:00",
        ),
        _mission(
            "mission-a",
            priority=MissionPriority.HIGH,
            status=MissionStatus.ASSIGNED,
            created_at="2026-01-02T00:00:00+00:00",
        ),
        _mission(
            "mission-old",
            priority=MissionPriority.HIGH,
            status=MissionStatus.ASSIGNED,
            created_at="2025-12-31T19:00:00-05:00",
        ),
        _mission(
            "mission-critical",
            priority=MissionPriority.CRITICAL,
            created_at="2026-01-03T00:00:00+00:00",
        ),
    ]

    result = rank_missions(missions)

    assert [entry.mission.mission_id for entry in result.missions] == [
        "mission-critical",
        "mission-old",
        "mission-a",
        "mission-b",
        "mission-z",
    ]
    assert result.risk_data_available is False
    assert result.missing_risk_disaster_ids == ["disaster-001"]
    assert "disaster risk unassessed" in result.ranking_basis
    assert all(entry.disaster_risk_score is None for entry in result.missions)


def test_ranking_without_calculated_scores_keeps_existing_manual_order() -> None:
    missions = [
        _mission("mission-low", priority=MissionPriority.LOW),
        _mission("mission-high", priority=MissionPriority.HIGH),
    ]

    result = rank_missions(missions)

    assert [entry.mission.mission_id for entry in result.missions] == [
        "mission-high",
        "mission-low",
    ]
    assert result.risk_data_available is False
    assert result.missing_risk_disaster_ids == ["disaster-001"]
    assert all(entry.disaster_risk_score is None for entry in result.missions)


def test_terminal_statuses_sort_after_active_statuses_for_equal_priority() -> None:
    missions = [
        _mission("mission-cancelled", status=MissionStatus.CANCELLED),
        _mission("mission-completed", status=MissionStatus.COMPLETED),
        _mission("mission-arrived", status=MissionStatus.ARRIVED),
    ]

    result = rank_missions(missions)

    assert [entry.mission.mission_id for entry in result.missions] == [
        "mission-arrived",
        "mission-completed",
        "mission-cancelled",
    ]


@pytest.mark.parametrize(
    "risk_scores",
    [
        {"disaster-001": -0.01},
        {"disaster-001": 100.01},
        {"disaster-001": float("nan")},
        {"disaster-001": float("inf")},
        {"disaster-001": True},
        {"unknown-disaster": 50.0},
        {"": 50.0},
    ],
)
def test_invalid_risk_score_inputs_are_rejected(
    risk_scores: dict[str, float],
) -> None:
    with pytest.raises(ValueError):
        rank_missions([_mission("mission-1")], risk_scores)


def test_invalid_creation_time_is_rejected() -> None:
    with pytest.raises(ValueError, match="not valid ISO-8601"):
        rank_missions([_mission("mission-invalid-time", created_at="not-a-timestamp")])


def test_duplicate_mission_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        rank_missions([_mission("mission-duplicate"), _mission("mission-duplicate")])
