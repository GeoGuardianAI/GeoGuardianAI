"""GeoGuardian Member 1 disaster-detection API."""
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI
from routes import change_detection, detection, heatmap, segmentation, tracking, upload
from services.bytetrack_service import ByteTrackService
from services.sam_service import SamService
from services.repository import DetectionRepository
from services.yolo_service import YoloService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    storage = Path(__file__).parent / "data"
    storage.mkdir(parents=True, exist_ok=True)
    app.state.repository = DetectionRepository(storage / "detections.db")
    app.state.repository.initialize()
    app.state.yolo_service = YoloService()
    app.state.sam_service = SamService()
    app.state.tracker = ByteTrackService(app.state.yolo_service)
    storage.joinpath("uploads").mkdir(parents=True, exist_ok=True)
    app.state.uploads = {
        asset["asset_id"]: asset["path"]
        for asset in app.state.repository.list_assets()
        if Path(str(asset["path"])).is_file()
    }
    yield
    app.state.repository.close()

app = FastAPI(title="GeoGuardian Detection API", version="1.0.0", lifespan=lifespan)
app.include_router(upload.router)
app.include_router(detection.router)
app.include_router(segmentation.router)
app.include_router(change_detection.router)
app.include_router(tracking.router)
app.include_router(heatmap.router)

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "disaster-detection"}
