from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..services.assets import upload_path
from backend.rescue.services.disaster_classifier import (
    ClassifierUnavailableError,
    InvalidImageError,
    classify_image,
)

router = APIRouter(tags=["classification"])


class ClassificationRequest(BaseModel):
    asset_id: str


@router.post("/classify-image")
def classify_uploaded_image(
    payload: ClassificationRequest,
    request: Request,
) -> dict[str, object]:
    image_path = upload_path(request, payload.asset_id)
    try:
        result = classify_image(image_path)
    except InvalidImageError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ClassifierUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "asset_id": payload.asset_id,
        "predicted_class": result.predicted_class,
        "confidence": result.confidence,
        "probabilities": result.probabilities,
        "device": result.device,
        "note": (
            "Image-level prediction; confidence is uncalibrated and is not a "
            "verified damage assessment."
        ),
    }
