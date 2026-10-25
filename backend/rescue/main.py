import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.rescue.integrations.member1_detection.routes import (
    change_detection,
    detection,
    heatmap,
    segmentation,
    tracking,
    upload,
)
from backend.rescue.integrations.member1_detection.services.repository import (
    DetectionRepository,
)
from backend.rescue.api.deployment import router as deployment_router
from backend.rescue.api.audit_events import router as audit_events_router
from backend.rescue.api.detection_integration import router as detection_integration_router
from backend.rescue.api.emergency_resources import router as emergency_resources_router
from backend.rescue.api.emergency_vehicles import router as emergency_vehicles_router
from backend.rescue.api.hospitals import router as hospitals_router
from backend.rescue.api.missions import router as missions_router
from backend.rescue.api.resources import router as resource_router
from backend.rescue.api.risk_priority import router as risk_priority_router
from backend.rescue.api.routes import router as routes_router
from backend.rescue.api.rescue_teams import router as rescue_teams_router
from backend.rescue.api.shelters import router as shelters_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    default_database_path = (
        Path(__file__).resolve().parent / "data" / "detection.sqlite3"
    )
    database_path = Path(
        os.environ.get("GEOGUARDIAN_DETECTION_DATABASE_PATH", default_database_path)
    )
    database_path.parent.mkdir(parents=True, exist_ok=True)
    (database_path.parent / "uploads").mkdir(parents=True, exist_ok=True)

    repository = DetectionRepository(database_path)
    try:
        repository.initialize()
        app.state.repository = repository
        app.state.uploads = {}
        yield
    finally:
        repository.close()


app = FastAPI(
    title="GeoGuardian AI - Resource Management API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hospitals_router)
app.include_router(missions_router)
app.include_router(audit_events_router)
app.include_router(detection_integration_router)
app.include_router(emergency_vehicles_router)
app.include_router(emergency_resources_router)
app.include_router(deployment_router)
app.include_router(resource_router)
app.include_router(risk_priority_router)
app.include_router(routes_router)
app.include_router(rescue_teams_router)
app.include_router(shelters_router)
app.include_router(upload.router)
app.include_router(detection.router)
app.include_router(heatmap.router)
app.include_router(segmentation.router)
app.include_router(change_detection.router)
app.include_router(tracking.router)


@app.get("/health", response_model=dict[str, str])
async def health() -> dict[str, str]:
    """Health check endpoint for the resource-management service."""
    return {
        "status": "ok",
        "service": "resource-management",
    }