from fastapi import APIRouter, HTTPException, Request
from models.schemas import SegmentationRequest
from services.assets import upload_path
from services.raster_service import RasterService
router = APIRouter(tags=["segmentation"])

@router.post("/segment")
async def segment(payload: SegmentationRequest, request: Request) -> dict:
    try:
        image = RasterService().read(upload_path(request, payload.asset_id))
        return request.app.state.sam_service.segment(image, payload.points, payload.box)
    except (ValueError, RuntimeError, NotImplementedError) as exc:
        raise HTTPException(422, detail=str(exc)) from exc
