import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from models.schemas import AnalysisRequest, DetectionJob, Incident
from services.assets import upload_path
from services.damage_service import DamageAssessmentService
from services.raster_service import RasterService
router = APIRouter(tags=["detection"]); logger = logging.getLogger(__name__)

def _analyze(path, payload: AnalysisRequest, source_file: str, detector) -> Incident:
    raster = RasterService()
    image = raster.preprocess(raster.read(path))
    coordinates = payload.coordinates or raster.geospatial_center(path)
    incident = DamageAssessmentService().assess(
        detector.detect(image),
        coordinates,
        payload.location,
        payload.asset_id,
        source_file,
    )
    incident.model_name = detector.model_name
    return incident

@router.post("/detect", response_model=Incident)
async def detect(payload: AnalysisRequest, request: Request) -> Incident:
    try:
        path = upload_path(request, payload.asset_id)
        asset = request.app.state.repository.get_asset(payload.asset_id)
        source_file = str(asset["filename"]) if asset else path.name
        async with request.app.state.inference_semaphore:
            incident = await asyncio.to_thread(
                _analyze, path, payload, source_file, request.app.state.yolo_service
            )
        request.app.state.repository.save(incident)
        return incident
    except (ValueError, RuntimeError) as exc:
        logger.warning("Detection request rejected: %s", exc)
        raise HTTPException(422, detail=str(exc)) from exc

async def _process_detection_job(
    request: Request,
    job_id: str,
    payload: AnalysisRequest,
    path,
    source_file: str,
) -> None:
    repository = request.app.state.repository
    job = repository.get_job(job_id)
    if job is None:
        logger.error("Detection job disappeared before processing: %s", job_id)
        return
    job.status = "running"
    job.updated_at = datetime.now(timezone.utc)
    repository.save_job(job)
    try:
        async with request.app.state.inference_semaphore:
            incident = await asyncio.to_thread(
                _analyze, path, payload, source_file, request.app.state.yolo_service
            )
        repository.save(incident)
        job.status = "completed"
        job.result = incident
        job.updated_at = datetime.now(timezone.utc)
        repository.save_job(job)
    except (ValueError, RuntimeError) as exc:
        logger.warning("Detection job %s failed: %s", job_id, exc)
        job.status = "failed"
        job.error = str(exc)
        job.updated_at = datetime.now(timezone.utc)
        repository.save_job(job)
    except Exception:
        logger.exception("Unexpected failure processing detection job %s", job_id)
        job.status = "failed"
        job.error = "Unexpected inference error; check the API logs."
        job.updated_at = datetime.now(timezone.utc)
        repository.save_job(job)

@router.post("/jobs/detection", response_model=DetectionJob, status_code=202)
async def create_detection_job(payload: AnalysisRequest, request: Request) -> DetectionJob:
    try:
        path = upload_path(request, payload.asset_id)
    except HTTPException:
        raise
    asset = request.app.state.repository.get_asset(payload.asset_id)
    now = datetime.now(timezone.utc)
    job = DetectionJob(
        job_id=f"JOB-{uuid4().hex}",
        status="queued",
        created_at=now,
        updated_at=now,
    )
    request.app.state.repository.save_job(job)
    task = asyncio.create_task(
        _process_detection_job(
            request,
            job.job_id,
            payload,
            path,
            str(asset["filename"]) if asset else path.name,
        )
    )
    request.app.state.detection_tasks[job.job_id] = task
    task.add_done_callback(lambda _task: request.app.state.detection_tasks.pop(job.job_id, None))
    return job

@router.get("/jobs/{job_id}", response_model=DetectionJob)
async def detection_job(job_id: str, request: Request) -> DetectionJob:
    job = request.app.state.repository.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Detection job not found")
    return job

@router.websocket("/ws/detection/{job_id}")
async def detection_job_updates(websocket: WebSocket, job_id: str) -> None:
    repository = websocket.app.state.repository
    if repository.get_job(job_id) is None:
        await websocket.close(code=4404, reason="Detection job not found")
        return
    await websocket.accept()
    try:
        while True:
            job = repository.get_job(job_id)
            if job is None:
                await websocket.send_json({"job_id": job_id, "status": "failed", "error": "Detection job not found"})
                return
            await websocket.send_json(job.model_dump(mode="json"))
            if job.status in {"completed", "failed"}:
                return
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from detection job %s", job_id)

@router.get("/detections", response_model=list[Incident])
async def detections(request: Request, limit: int = 100) -> list[Incident]:
    return request.app.state.repository.list(min(max(limit, 1), 500))

@router.get("/detections/{incident_id}", response_model=Incident)
async def detection_by_id(incident_id: str, request: Request) -> Incident:
    incident = request.app.state.repository.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    return incident
