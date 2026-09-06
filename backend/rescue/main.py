from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.rescue.api.deployment import router as deployment_router
from backend.rescue.api.emergency_resources import router as emergency_resources_router
from backend.rescue.api.emergency_vehicles import router as emergency_vehicles_router
from backend.rescue.api.hospitals import router as hospitals_router
from backend.rescue.api.resources import router as resource_router
from backend.rescue.api.risk_priority import router as risk_priority_router
from backend.rescue.api.routes import router as routes_router
from backend.rescue.api.rescue_teams import router as rescue_teams_router
from backend.rescue.api.shelters import router as shelters_router

app = FastAPI(
    title="GeoGuardian AI - Resource Management API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hospitals_router)
app.include_router(emergency_vehicles_router)
app.include_router(emergency_resources_router)
app.include_router(deployment_router)
app.include_router(resource_router)
app.include_router(risk_priority_router)
app.include_router(routes_router)
app.include_router(rescue_teams_router)
app.include_router(shelters_router)


@app.get("/health", response_model=dict[str, str])
async def health() -> dict[str, str]:
    """Health check endpoint for the resource-management service."""
    return {
        "status": "ok",
        "service": "resource-management",
    }