import logging
from fastapi import APIRouter, HTTPException, Request
from models.schemas import AnalysisRequest, Incident
from services.assets import upload_path
from services.damage_service import DamageAssessmentService
from services.raster_service import RasterService
from services.yolo_service import YoloService
router = APIRouter(tags=["detection"]); logger = logging.getLogger(__name__)

@router.post("/detect", response_model=Incident)
async def detect(payload: AnalysisRequest, request: Request) -> Incident:
    try:
        image = RasterService().preprocess(RasterService().read(upload_path(request, payload.asset_id)))
        incident = DamageAssessmentService().assess(YoloService().detect(image), payload.coordinates, payload.location)
        request.app.state.repository.save(incident)
        return incident
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, detail=str(exc)) from exc

@router.get("/detections", response_model=list[Incident])
async def detections(request: Request, limit: int = 100) -> list[Incident]:
    return request.app.state.repository.list(min(max(limit, 1), 500))
