import base64
import os
from pathlib import Path

import cv2
import numpy as np

from models.schemas import BoundingBox, PointPrompt


class SamService:
    """Optional SAM2 image predictor; runtime and checkpoints are deployment-managed."""

    def __init__(self) -> None:
        self._predictor = None
        self._configuration: tuple[str, str, str] | None = None

    def segment(
        self,
        image: np.ndarray,
        points: list[PointPrompt],
        box: BoundingBox | None,
    ) -> dict:
        checkpoint = os.getenv("GEOGUARDIAN_SAM2_CHECKPOINT")
        config = os.getenv("GEOGUARDIAN_SAM2_CONFIG")
        if not checkpoint or not config:
            raise RuntimeError(
                "SAM2 is not configured. Set GEOGUARDIAN_SAM2_CHECKPOINT and GEOGUARDIAN_SAM2_CONFIG."
            )
        if not Path(checkpoint).is_file():
            raise RuntimeError(f"SAM2 checkpoint does not exist: {checkpoint}")
        if not Path(config).is_file():
            raise RuntimeError(f"SAM2 configuration does not exist: {config}")
        if not points and box is None:
            raise ValueError("Provide at least one foreground/background point or a bounding box prompt.")

        height, width = image.shape[:2]
        if any(point.x >= width or point.y >= height for point in points):
            raise ValueError("Segmentation prompt points must lie within the image bounds.")
        prompt_box = None
        if box is not None:
            if box.x1 < 0 or box.y1 < 0 or box.x2 > width or box.y2 > height or box.x1 >= box.x2 or box.y1 >= box.y2:
                raise ValueError("Segmentation prompt box must be a non-empty box inside the image.")
            prompt_box = np.array([box.x1, box.y1, box.x2, box.y2], dtype=np.float32)

        try:
            import torch
            from sam2.build_sam import build_sam2
            from sam2.sam2_image_predictor import SAM2ImagePredictor
        except ImportError as exc:
            raise RuntimeError(
                "SAM2 and PyTorch are unavailable. Install the SAM2 runtime to segment images."
            ) from exc

        device = "cuda" if torch.cuda.is_available() else "cpu"
        configuration = (config, checkpoint, device)
        if self._predictor is None or self._configuration != configuration:
            self._predictor = SAM2ImagePredictor(build_sam2(config, checkpoint, device=device))
            self._configuration = configuration
        predictor = self._predictor
        predictor.set_image(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        point_coords = np.array([[point.x, point.y] for point in points], dtype=np.float32) if points else None
        point_labels = np.array([point.label for point in points], dtype=np.int32) if points else None
        masks, scores, _ = predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            box=prompt_box,
            multimask_output=True,
        )
        best = int(np.argmax(scores))
        mask = masks[best].astype(bool)
        mask_image = mask.astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boundaries = [
            cv2.approxPolyDP(contour, 1.0, True).reshape(-1, 2).tolist()
            for contour in contours
            if len(contour) >= 3
        ]
        success, encoded = cv2.imencode(".png", mask_image)
        if not success:
            raise RuntimeError("Unable to encode segmentation mask.")
        return {
            "model": "sam2",
            "confidence": float(scores[best]),
            "area_pixels": int(np.count_nonzero(mask)),
            "mask_png": f"data:image/png;base64,{base64.b64encode(encoded).decode('ascii')}",
            "boundaries": boundaries,
        }
