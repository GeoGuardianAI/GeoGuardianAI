"""YOLO adapter. Set GEOGUARDIAN_YOLO_WEIGHTS to enable a trained Ultralytics model."""
import os
import logging
from pathlib import Path
import numpy as np
from models.schemas import BoundingBox, DetectedObject
logger = logging.getLogger(__name__)

class YoloService:
    def __init__(self) -> None:
        self._model = None
        self.model_name = "configured-yolo"

    def _load(self):
        if self._model is None:
            weights = os.getenv("GEOGUARDIAN_YOLO_WEIGHTS")
            if not weights: raise RuntimeError("YOLO weights are not configured. Set GEOGUARDIAN_YOLO_WEIGHTS.")
            if not Path(weights).is_file():
                raise RuntimeError(f"YOLO weights file does not exist: {weights}")
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise RuntimeError("Ultralytics is unavailable. Install it to run YOLO inference.") from exc
            self._model = YOLO(weights)
            self.model_name = Path(weights).stem
        return self._model

    def detect(self, image: np.ndarray) -> list[DetectedObject]:
        model = self._load()
        try:
            confidence = float(os.getenv("GEOGUARDIAN_YOLO_CONFIDENCE", "0.25"))
        except ValueError as exc:
            raise RuntimeError("GEOGUARDIAN_YOLO_CONFIDENCE must be a number between 0 and 1.") from exc
        if not 0 <= confidence <= 1:
            raise RuntimeError("GEOGUARDIAN_YOLO_CONFIDENCE must be between 0 and 1.")
        result = model(image, verbose=False, conf=confidence)[0]
        names = result.names
        return [DetectedObject(class_name=str(names[int(box.cls[0])]), confidence=round(float(box.conf[0]), 4), bbox=BoundingBox(x1=float(box.xyxy[0][0]), y1=float(box.xyxy[0][1]), x2=float(box.xyxy[0][2]), y2=float(box.xyxy[0][3]))) for box in result.boxes]

    def track_frame(self, image: np.ndarray) -> list[DetectedObject]:
        model = self._load()
        try:
            confidence = float(os.getenv("GEOGUARDIAN_YOLO_CONFIDENCE", "0.25"))
        except ValueError as exc:
            raise RuntimeError("GEOGUARDIAN_YOLO_CONFIDENCE must be a number between 0 and 1.") from exc
        if not 0 <= confidence <= 1:
            raise RuntimeError("GEOGUARDIAN_YOLO_CONFIDENCE must be between 0 and 1.")
        result = model.track(
            image,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False,
            conf=confidence,
        )[0]
        names = result.names
        return [
            DetectedObject(
                class_name=str(names[int(box.cls[0])]),
                confidence=round(float(box.conf[0]), 4),
                bbox=BoundingBox(
                    x1=float(box.xyxy[0][0]),
                    y1=float(box.xyxy[0][1]),
                    x2=float(box.xyxy[0][2]),
                    y2=float(box.xyxy[0][3]),
                ),
                track_id=int(box.id[0]) if box.id is not None else None,
            )
            for box in result.boxes
        ]

    def reset_tracker(self) -> None:
        if self._model is None:
            return
        predictor = getattr(self._model, "predictor", None)
        for tracker in getattr(predictor, "trackers", []):
            tracker.reset()
