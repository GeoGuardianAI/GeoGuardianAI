"""Response models for deterministic mission ranking."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.rescue.models.mission import Mission


class RankedMission(BaseModel):
    """A mission and the ranking metadata derived from available information."""

    rank: int = Field(..., ge=1, description="One-based position in the ranked list")
    mission: Mission = Field(..., description="The existing mission record")
    disaster_risk_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Integrated disaster risk score, when available",
    )


class MissionRankingResponse(BaseModel):
    """Ranked missions and an explicit indication of risk-data availability."""

    risk_data_available: bool = Field(
        ..., description="Whether any mission has an integrated disaster risk score"
    )
    missing_risk_disaster_ids: list[str] = Field(
        ..., description="Disaster identifiers without an integrated risk score"
    )
    ranking_basis: str = Field(
        ..., description="Ordering rules applied to produce this ranked list"
    )
    missions: list[RankedMission] = Field(
        ..., description="Missions ordered by the stated ranking rules"
    )
