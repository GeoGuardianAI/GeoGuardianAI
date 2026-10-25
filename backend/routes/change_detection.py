import asyncio
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
        before = raster.read(upload_path(request, payload.before_asset_id))
        after = raster.read(upload_path(request, payload.after_asset_id))
        return await asyncio.to_thread(ChangeFormerService().compare, before, after)
    except (ValueError, RuntimeError) as exc: raise HTTPException(422, detail=str(exc)) from exc
