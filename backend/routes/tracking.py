from fastapi import APIRouter, HTTPException, Request
from models.schemas import TrackRequest
from services.assets import upload_path
from services.bytetrack_service import ByteTrackService
router = APIRouter(tags=["tracking"])

@router.post("/track")
async def track(payload: TrackRequest, request: Request) -> dict:
    try:
        path = upload_path(request, payload.asset_id)
        return request.app.state.tracker.track(path, payload.max_frames, payload.frame_stride)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, detail=str(exc)) from exc
