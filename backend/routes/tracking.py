import cv2
from fastapi import APIRouter, HTTPException, Request
from models.schemas import TrackRequest
from services.assets import upload_path
from services.bytetrack_service import ByteTrackService
router = APIRouter(tags=["tracking"])

@router.post("/track")
async def track(payload: TrackRequest, request: Request) -> dict:
    path = upload_path(request, payload.asset_id); capture = cv2.VideoCapture(str(path))
    if not capture.isOpened(): raise HTTPException(422, "The supplied asset is not a readable video")
    count = 0
    while count < payload.max_frames and capture.read()[0]: count += 1
    capture.release()
    try: return ByteTrackService().track(count)
    except RuntimeError as exc: raise HTTPException(422, detail=str(exc)) from exc
