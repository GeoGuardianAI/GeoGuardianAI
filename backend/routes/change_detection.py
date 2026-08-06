from fastapi import APIRouter, HTTPException, Request
from models.schemas import ChangeRequest
from services.assets import upload_path
from services.changeformer_service import ChangeFormerService
from services.raster_service import RasterService
router = APIRouter(tags=["change detection"])

@router.post("/change-detection")
async def change_detection(payload: ChangeRequest, request: Request) -> dict:
    try:
        raster = RasterService()
        return ChangeFormerService().compare(raster.read(upload_path(request, payload.before_asset_id)), raster.read(upload_path(request, payload.after_asset_id)))
    except ValueError as exc: raise HTTPException(422, detail=str(exc)) from exc
