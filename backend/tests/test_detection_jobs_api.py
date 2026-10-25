import asyncio
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes.detection import router
from services.repository import DetectionRepository


class FakeDetector:
    model_name = "test-model"

    def detect(self, image: np.ndarray) -> list:
        return []


def test_detection_job_runs_and_streams_completion(tmp_path: Path) -> None:
    image_path = tmp_path / "scene.png"
    assert cv2.imwrite(str(image_path), np.zeros((16, 16, 3), dtype=np.uint8))

    repository = DetectionRepository(tmp_path / "detections.db")
    repository.initialize()
    repository.save_asset(
        {
            "asset_id": "image-test",
            "path": str(image_path),
            "filename": "scene.png",
            "kind": "image",
            "content_type": "image/png",
            "bytes": image_path.stat().st_size,
        }
    )

    application = FastAPI()
    application.include_router(router)
    application.state.repository = repository
    application.state.uploads = {"image-test": str(image_path)}
    application.state.yolo_service = FakeDetector()
    application.state.inference_semaphore = asyncio.Semaphore(1)
    application.state.detection_tasks = {}

    try:
        with TestClient(application) as client:
            response = client.post(
                "/jobs/detection",
                json={"asset_id": "image-test"},
            )
            assert response.status_code == 202
            job_id = response.json()["job_id"]

            with client.websocket_connect(f"/ws/detection/{job_id}") as websocket:
                message = websocket.receive_json()
                while message["status"] not in {"completed", "failed"}:
                    message = websocket.receive_json()

            assert message["status"] == "completed"
            assert message["result"]["source_file"] == "scene.png"
            assert message["result"]["model_name"] == "test-model"
            assert client.get(f"/jobs/{job_id}").json()["status"] == "completed"
            assert client.get("/detections").json()[0]["source_asset_id"] == "image-test"
    finally:
        repository.close()
