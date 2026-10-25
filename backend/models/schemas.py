from datetime import datetime
from typing import Literal
from pydantic import AliasChoices, BaseModel, Field, computed_field

class Coordinates(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)

class BoundingBox(BaseModel):
    x1: float; y1: float; x2: float; y2: float

class DetectedObject(BaseModel):
    class_name: str = Field(
        validation_alias=AliasChoices("class", "class_name"),
        serialization_alias="class",
    )
    confidence: float = Field(ge=0, le=1)
    bbox: BoundingBox | None = None
    track_id: int | None = None

class Incident(BaseModel):
    incident_id: str
    disaster: Literal["Flood", "Fire", "Infrastructure damage", "No significant disaster"]
    location: str | None = None
    confidence: float = Field(ge=0, le=1)
    affected_area_sqkm: float = Field(ge=0)
    damaged_buildings: int = Field(ge=0)
    damaged_roads: list[str] = Field(default_factory=list)
    damaged_bridges: list[str] = Field(default_factory=list)
    detected_objects: list[DetectedObject] = Field(default_factory=list)
    coordinates: Coordinates | None = None
    source_asset_id: str | None = None
    source_file: str | None = None
    model_name: str = "unknown"
    processing_status: Literal["completed"] = "completed"
    timestamp: datetime

    @computed_field
    @property
    def geojson_geometry(self) -> dict[str, object] | None:
        if self.coordinates is None:
            return None
        return {
            "type": "Point",
            "coordinates": [self.coordinates.lng, self.coordinates.lat],
        }

class DetectionJob(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: datetime
    updated_at: datetime
    result: Incident | None = None
    error: str | None = None

class AnalysisRequest(BaseModel):
    asset_id: str
    coordinates: Coordinates | None = None
    location: str | None = Field(default=None, max_length=160)

class ChangeRequest(BaseModel):
    before_asset_id: str
    after_asset_id: str
    coordinates: Coordinates | None = None
    location: str | None = None

class TrackRequest(BaseModel):
    asset_id: str
    max_frames: int = Field(default=300, ge=1, le=3000)
    frame_stride: int = Field(default=10, ge=1, le=300)

class PointPrompt(BaseModel):
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    label: Literal[0, 1] = 1

class SegmentationRequest(AnalysisRequest):
    points: list[PointPrompt] = Field(default_factory=list, max_length=32)
    box: BoundingBox | None = None
