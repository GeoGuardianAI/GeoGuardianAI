from fastapi import FastAPI

app = FastAPI(
    title="GeoGuardian AI - Resource Management API",
    version="0.1.0",
)


@app.get("/health", response_model=dict[str, str])
async def health() -> dict[str, str]:
    """Health check endpoint for the resource-management service."""
    return {
        "status": "ok",
        "service": "resource-management",
    }