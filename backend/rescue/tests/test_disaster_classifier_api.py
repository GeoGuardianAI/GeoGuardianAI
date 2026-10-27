from fastapi.testclient import TestClient

from backend.rescue.integrations.member1_detection.routes import classification
from backend.rescue.main import app
from backend.rescue.services.disaster_classifier import (
    ClassificationResult,
    InvalidImageError,
)

client = TestClient(app)


def test_classify_image_returns_mocked_prediction(tmp_path, monkeypatch) -> None:
    image_path = tmp_path / "uploaded.png"
    image_path.write_bytes(b"mocked image")
    monkeypatch.setattr(
        app.state,
        "uploads",
        {"image-test": str(image_path)},
        raising=False,
    )

    def mock_classify(path):
        assert path == image_path
        return ClassificationResult(
            predicted_class="flood",
            confidence=0.8,
            probabilities={"flood": 0.8, "wildfire": 0.2},
            device="cpu",
        )

    monkeypatch.setattr(
        classification,
        "classify_image",
        mock_classify,
    )

    response = client.post("/classify-image", json={"asset_id": "image-test"})

    assert response.status_code == 200
    assert response.json() == {
        "asset_id": "image-test",
        "predicted_class": "flood",
        "confidence": 0.8,
        "probabilities": {"flood": 0.8, "wildfire": 0.2},
        "device": "cpu",
        "note": (
            "Image-level prediction; confidence is uncalibrated and is not a "
            "verified damage assessment."
        ),
    }


def test_classify_image_rejects_missing_asset(monkeypatch) -> None:
    monkeypatch.setattr(app.state, "uploads", {}, raising=False)

    response = client.post(
        "/classify-image",
        json={"asset_id": "image-missing"},
    )

    assert response.status_code == 404
    assert "Unknown asset_id" in response.json()["detail"]


def test_classify_image_rejects_unreadable_image(tmp_path, monkeypatch) -> None:
    image_path = tmp_path / "invalid.png"
    image_path.write_bytes(b"not an image")
    monkeypatch.setattr(
        app.state,
        "uploads",
        {"image-invalid": str(image_path)},
        raising=False,
    )

    def reject_image(path):
        raise InvalidImageError(f"Unable to read a valid image: {path}")

    monkeypatch.setattr(classification, "classify_image", reject_image)

    response = client.post(
        "/classify-image",
        json={"asset_id": "image-invalid"},
    )

    assert response.status_code == 422
    assert "Unable to read a valid image" in response.json()["detail"]
