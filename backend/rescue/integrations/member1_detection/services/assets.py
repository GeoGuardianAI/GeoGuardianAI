from pathlib import Path
from fastapi import HTTPException, Request

def upload_path(request: Request, asset_id: str) -> Path:
    path = Path(request.app.state.uploads.get(asset_id, ""))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Unknown asset_id. Upload a file before analysis.")
    return path
