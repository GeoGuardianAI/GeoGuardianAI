import logging
from fastapi import APIRouter, HTTPException, Request
from models.schemas import AnalysisRequest, Incident
from services.assets import upload_path
from services.damage_service import DamageAssessmentService
from services.raster_service import RasterService
router = APIRouter(tags=["detection"]); logger = logging.getLogger(__name__)

@router.post("/detect", response_model=Incident)
async def detect(payload: AnalysisRequest, request: Request) -> Incident:
    try:
        path = upload_path(request, payload.asset_id)
        raster = RasterService()
        image = raster.preprocess(raster.read(path))
        coordinates = payload.coordinates or raster.geospatial_center(path)
        detector = request.app.state.yolo_service
        asset = request.app.state.repository.get_asset(payload.asset_id)
        incident = DamageAssessmentService().assess(
            detector.detect(image),
            coordinates,
            payload.location,
            payload.asset_id,
            str(asset["filename"]) if asset else path.name,
        )
        incident.model_name = detector.model_name
        request.app.state.repository.save(incident)
        return incident
    except (ValueError, RuntimeError) as exc:
        logger.warning("Detection request rejected: %s", exc)
        raise HTTPException(422, detail=str(exc)) from exc

@router.get("/detections", response_model=list[Incident])
async def detections(request: Request, limit: int = 100) -> list[Incident]:
    return request.app.state.repository.list(min(max(limit, 1), 500))

@router.get("/detections/{incident_id}", response_model=Incident)
async def detection_by_id(incident_id: str, request: Request) -> Incident:
    incident = request.app.state.repository.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    return incident
