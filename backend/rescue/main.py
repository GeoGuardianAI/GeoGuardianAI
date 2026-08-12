from fastapi import FastAPI

from backend.rescue.api.hospitals import router as hospitals_router

app = FastAPI(
    title="GeoGuardian AI - Resource Management API",
    version="0.1.0",
)

app.include_router(hospitals_router)


@app.get("/health", response_model=dict[str, str])
async def health() -> dict[str, str]:
    """Health check endpoint for the resource-management service."""
    return {
        "status": "ok",
        "service": "resource-management",
    }