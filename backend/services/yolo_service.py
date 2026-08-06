"""YOLO adapter. Set GEOGUARDIAN_YOLO_WEIGHTS to enable a trained Ultralytics model."""
import os
import logging
from pathlib import Path
import numpy as np
from models.schemas import BoundingBox, DetectedObject
logger = logging.getLogger(__name__)

class YoloService:
    def __init__(self) -> None: self._model = None
    def _load(self):
        if self._model is None:
            weights = os.getenv("GEOGUARDIAN_YOLO_WEIGHTS")
            if not weights: raise RuntimeError("YOLO weights are not configured. Set GEOGUARDIAN_YOLO_WEIGHTS.")
            from ultralytics import YOLO
            self._model = YOLO(weights)
        return self._model
    def detect(self, image: np.ndarray) -> list[DetectedObject]:
        model = self._load()
        result = model(image, verbose=False)[0]
        names = result.names
        return [DetectedObject(class_name=str(names[int(box.cls[0])]), confidence=round(float(box.conf[0]), 4), bbox=BoundingBox(x1=float(box.xyxy[0][0]), y1=float(box.xyxy[0][1]), x2=float(box.xyxy[0][2]), y2=float(box.xyxy[0][3]))) for box in result.boxes]
