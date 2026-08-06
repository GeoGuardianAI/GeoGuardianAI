from models.schemas import DetectedObject

class ByteTrackService:
    """Adapter boundary: inject detector observations into a configured ByteTrack runtime."""
    def track(self, frames: int) -> dict:
        raise RuntimeError(
            "ByteTrack runtime is not configured. Register a detector and tracker implementation "
            "in ByteTrackService before requesting video tracks."
        )
