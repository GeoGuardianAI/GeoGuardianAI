from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class Coordinates(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)

class BoundingBox(BaseModel):
    x1: float; y1: float; x2: float; y2: float

class DetectedObject(BaseModel):
    class_name: str = Field(serialization_alias="class")
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
    damaged_roads: list[str] = []
    damaged_bridges: list[str] = []
    detected_objects: list[DetectedObject] = []
    coordinates: Coordinates
    timestamp: datetime

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
