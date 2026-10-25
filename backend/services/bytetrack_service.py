from pathlib import Path

import cv2

from services.yolo_service import YoloService


class ByteTrackService:
    """Run configured YOLO detections with ByteTrack on sampled video frames."""

    def __init__(self, detector: YoloService | None = None) -> None:
        self.detector = detector or YoloService()

    def track(self, path: Path, max_frames: int, frame_stride: int) -> dict:
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise ValueError("The supplied asset is not a readable video.")

        detector = self.detector
        observations: list[dict] = []
        decoded = 0
        sampled = 0
        fps = capture.get(cv2.CAP_PROP_FPS)
        detector.reset_tracker()
        try:
            while decoded < max_frames:
                ok, frame = capture.read()
                if not ok:
                    break
                frame_index = decoded
                decoded += 1
                if frame_index % frame_stride:
                    continue
                objects = detector.track_frame(frame)
                sampled += 1
                observations.extend(
                    {
                        **item.model_dump(by_alias=True),
                        "frame_index": frame_index,
                        "timestamp_seconds": round(frame_index / fps, 3) if fps > 0 else None,
                    }
                    for item in objects
                )
        finally:
            capture.release()
            detector.reset_tracker()
        return {
            "model": f"{detector.model_name}+bytetrack",
            "decoded_frames": decoded,
            "frames_processed": sampled,
            "frame_stride": frame_stride,
            "detections": observations,
        }
