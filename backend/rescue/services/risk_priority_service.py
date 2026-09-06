"""Deterministic disaster risk-priority scoring service."""

from __future__ import annotations

from backend.rescue.models.risk_priority import (
    PriorityLevel,
    RiskPriorityRequest,
    RiskPriorityResult,
)

POPULATION_CAP = 10_000
SEVERITY_WEIGHT = 0.50
POPULATION_WEIGHT = 0.30
INFRASTRUCTURE_WEIGHT = 0.20


def calculate_risk_priority(request: RiskPriorityRequest) -> RiskPriorityResult:
    """Calculate a transparent, deterministic risk score for a disaster.

    Severity, affected population, and critical infrastructure contribute 50%,
    30%, and 20% respectively. Population is capped at 10,000 people for
    normalization, and the final score is clamped to the 0-100 range.
    """
    severity_score = ((request.severity - 1) / 4) * 100
    population_score = min(request.affected_population, POPULATION_CAP) / POPULATION_CAP * 100
    infrastructure_score = 100.0 if request.critical_infrastructure else 0.0

    risk_score = max(
        0.0,
        min(
            100.0,
            severity_score * SEVERITY_WEIGHT
            + population_score * POPULATION_WEIGHT
            + infrastructure_score * INFRASTRUCTURE_WEIGHT,
        ),
    )
    risk_score = round(risk_score, 2)
    priority_level = _priority_level_for_score(risk_score)

    infrastructure_text = "present" if request.critical_infrastructure else "not present"
    reasoning = (
        f"Severity contributes {severity_score:.2f}/100 at 50%; affected population "
        f"contributes {population_score:.2f}/100 at 30% using a cap of {POPULATION_CAP}; "
        f"critical infrastructure is {infrastructure_text} and contributes "
        f"{infrastructure_score:.2f}/100 at 20%. Final risk score is {risk_score:.2f}/100, "
        f"which maps to {priority_level.value} priority."
    )

    return RiskPriorityResult(
        disaster_id=request.disaster_id,
        risk_score=risk_score,
        priority_level=priority_level,
        reasoning=reasoning,
    )


def _priority_level_for_score(score: float) -> PriorityLevel:
    """Map a clamped risk score to its configured priority band."""
    if score < 25.0:
        return PriorityLevel.LOW
    if score < 50.0:
        return PriorityLevel.MEDIUM
    if score < 75.0:
        return PriorityLevel.HIGH
    return PriorityLevel.CRITICAL