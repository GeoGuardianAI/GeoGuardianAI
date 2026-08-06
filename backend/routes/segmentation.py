from fastapi import APIRouter, HTTPException, Request
from models.schemas import AnalysisRequest
from services.assets import upload_path
from services.raster_service import RasterService
from services.sam_service import SamService
router = APIRouter(tags=["segmentation"])

@router.post("/segment")
async def segment(payload: AnalysisRequest, request: Request) -> dict:
    try: return SamService().segment(RasterService().read(upload_path(request, payload.asset_id)))
    except (ValueError, RuntimeError, NotImplementedError) as exc: raise HTTPException(422, detail=str(exc)) from exc
