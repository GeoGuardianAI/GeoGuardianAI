from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from services.raster_service import RasterService

router = APIRouter(tags=["uploads"])
IMAGE_TYPES = {
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".tif": {"image/tiff", "image/geotiff", "application/octet-stream"},
    ".tiff": {"image/tiff", "image/geotiff", "application/octet-stream"},
}
VIDEO_TYPES = {
    ".mp4": {"video/mp4", "application/octet-stream"},
    ".mov": {"video/quicktime", "application/octet-stream"},
    ".avi": {"video/x-msvideo", "video/avi", "application/octet-stream"},
}

def _matches_signature(path: Path, suffix: str) -> bool:
    with path.open("rb") as uploaded:
        header = uploaded.read(12)
    if suffix in {".jpg", ".jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if suffix == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in {".tif", ".tiff"}:
        return header.startswith((b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"))
    if suffix in {".mp4", ".mov"}:
        return len(header) >= 8 and header[4:8] == b"ftyp"
    if suffix == ".avi":
        return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"AVI "
    return False

async def _save(request: Request, file: UploadFile, accepted: dict[str, set[str]], kind: str) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in accepted or file.content_type not in accepted[suffix]:
        raise HTTPException(415, f"Unsupported {kind} file type")
    asset_id = f"{kind}-{uuid4().hex}"
    destination = Path(request.app.state.repository.connection.execute("PRAGMA database_list").fetchone()[2]).parent / "uploads" / f"{asset_id}{suffix}"
    size = 0
    saved = False
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 2 * 1024 * 1024 * 1024:
                    raise HTTPException(413, "Asset exceeds 2GB limit")
                output.write(chunk)
        if size == 0:
            raise HTTPException(400, "Uploaded file is empty")
        if not _matches_signature(destination, suffix):
            raise HTTPException(422, "File contents do not match the declared media type")
        try:
            metadata = RasterService().metadata(destination) if kind == "image" else None
        except ValueError as exc:
            raise HTTPException(422, detail=str(exc)) from exc
        asset = {
            "asset_id": asset_id,
            "path": str(destination),
            "filename": Path(file.filename or "asset").name,
            "kind": kind,
            "content_type": file.content_type or "",
            "bytes": size,
        }
        request.app.state.repository.save_asset(asset)
        request.app.state.uploads[asset_id] = str(destination)
        saved = True
        response = {key: value for key, value in asset.items() if key != "path" and key != "kind"}
        if metadata is not None:
            response["metadata"] = metadata
        return response
    finally:
        if not saved:
            destination.unlink(missing_ok=True)

@router.post("/upload-image", status_code=201)
async def upload_image(request: Request, file: UploadFile = File(...)) -> dict:
    return await _save(request, file, IMAGE_TYPES, "image")

@router.post("/upload-video", status_code=201)
async def upload_video(request: Request, file: UploadFile = File(...)) -> dict:
    return await _save(request, file, VIDEO_TYPES, "video")
