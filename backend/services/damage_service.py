from datetime import datetime, timezone
from uuid import uuid4
from models.schemas import Coordinates, DetectedObject, Incident

class DamageAssessmentService:
    def assess(self, objects: list[DetectedObject], coords: Coordinates | None, location: str | None) -> Incident:
        flood = [o for o in objects if o.class_name.lower() in {"flood", "water", "fire", "smoke"}]
        damaged = [o for o in objects if "damag" in o.class_name.lower()]
        disaster = "Flood" if any(o.class_name.lower() in {"flood", "water"} for o in flood) else "Fire" if flood else "Infrastructure damage" if damaged else "No significant disaster"
        confidence = max((o.confidence for o in flood + damaged), default=0.0)
        return Incident(incident_id=f"INC-{uuid4().hex[:10].upper()}", disaster=disaster, location=location, confidence=confidence, affected_area_sqkm=0.0, damaged_buildings=len(damaged), detected_objects=objects, coordinates=coords or Coordinates(lat=0, lng=0), timestamp=datetime.now(timezone.utc))
