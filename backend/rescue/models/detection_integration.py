"""Validated adapter contract for operator-confirmed detection-to-mission handoff."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DisasterDetectionAdapter(BaseModel):
    """Fields accepted by the rescue adapter, not an upstream detection schema.

    Core identity, type, and coordinate fields reuse fields already present in
    rescue deployment and risk-priority requests. Optional risk context is
    accepted when supplied by an upstream adapter.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    detection_id: str = Field(
        ..., min_length=1, description="Stable source detection identifier"
    )
    disaster_id: str = Field(..., min_length=1)
    disaster_type: str = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude: float = Field(..., ge=-180.0, le=180.0, allow_inf_nan=False)
    severity: int | None = Field(default=None, ge=1, le=5, strict=True)
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, allow_inf_nan=False
    )
    affected_population: int | None = Field(default=None, ge=0, strict=True)
    critical_infrastructure: bool | None = None

    @field_validator("detection_id", "disaster_id", "disaster_type")
    @classmethod
    def validate_nonblank(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be blank")
        return value


class DetectionMissionLink(BaseModel):
    """Durable idempotency record linking a source detection to one mission."""

    model_config = ConfigDict(extra="forbid")

    detection_id: str
    mission_id: str
    detection: DisasterDetectionAdapter
