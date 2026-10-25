from fastapi import APIRouter, Request
router = APIRouter(tags=["heatmap"])

@router.get("/heatmap")
async def heatmap(request: Request) -> dict:
    incidents = request.app.state.repository.list(500)
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [i.coordinates.lng, i.coordinates.lat]}, "properties": {"incident_id": i.incident_id, "risk": i.confidence, "disaster": i.disaster, "timestamp": i.timestamp.isoformat()}} for i in incidents if i.coordinates.lat or i.coordinates.lng]}
