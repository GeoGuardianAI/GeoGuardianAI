from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

router = APIRouter(tags=["uploads"])
IMAGE_TYPES = {"image/jpeg", "image/png", "image/tiff", "image/geotiff"}
VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo"}

async def _save(request: Request, file: UploadFile, accepted: set[str], kind: str) -> dict:
    if file.content_type not in accepted: raise HTTPException(415, f"Unsupported {kind} content type: {file.content_type}")
    asset_id = f"{kind}-{uuid4().hex}"
    suffix = Path(file.filename or "asset").suffix.lower()
    destination = Path(request.app.state.repository.connection.execute("PRAGMA database_list").fetchone()[2]).parent / "uploads" / f"{asset_id}{suffix}"
    size = 0
    with destination.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > 2 * 1024 * 1024 * 1024: output.close(); destination.unlink(missing_ok=True); raise HTTPException(413, "Asset exceeds 2GB limit")
            output.write(chunk)
    if not hasattr(request.app.state, "uploads"): request.app.state.uploads = {}
    request.app.state.uploads[asset_id] = str(destination)
    return {"asset_id": asset_id, "filename": file.filename, "content_type": file.content_type, "bytes": size}

@router.post("/upload-image", status_code=201)
async def upload_image(request: Request, file: UploadFile = File(...)) -> dict:
    return await _save(request, file, IMAGE_TYPES, "image")

@router.post("/upload-video", status_code=201)
async def upload_video(request: Request, file: UploadFile = File(...)) -> dict:
    return await _save(request, file, VIDEO_TYPES, "video")
