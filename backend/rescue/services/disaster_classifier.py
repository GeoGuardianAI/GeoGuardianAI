from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any


class ClassifierUnavailableError(RuntimeError):
    """Raised when the classifier runtime or checkpoint is unavailable."""


class InvalidImageError(ValueError):
    """Raised when an uploaded file cannot be decoded as an image."""


@dataclass(frozen=True)
class ClassificationResult:
    predicted_class: str
    confidence: float
    probabilities: dict[str, float]
    device: str


@dataclass
class _LoadedClassifier:
    model: Any
    preprocessing: Any
    class_names: list[str]
    device: Any
    image_module: Any
    torch_module: Any


_DEFAULT_CHECKPOINT = (
    Path(__file__).resolve().parents[3]
    / "models"
    / "disaster_classifier"
    / "efficientnet_b0.pth"
)
_classifier_lock = Lock()
_loaded_classifier: _LoadedClassifier | None = None


def _load_classifier() -> _LoadedClassifier:
    checkpoint_path = Path(
        os.environ.get(
            "GEOGUARDIAN_CLASSIFIER_CHECKPOINT",
            str(_DEFAULT_CHECKPOINT),
        )
    )
    if not checkpoint_path.is_file():
        raise ClassifierUnavailableError(
            f"Classifier checkpoint not found: {checkpoint_path}"
        )

    try:
        import torch
        from PIL import Image
        from torch import nn
        from torchvision import models, transforms
    except (ImportError, OSError, RuntimeError) as exc:
        raise ClassifierUnavailableError(
            "Image classification requires working PyTorch, torchvision, and Pillow installations."
        ) from exc

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    class_names = checkpoint["class_names"]
    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(
        model.classifier[1].in_features,
        len(class_names),
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device).eval()

    preprocessing = transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(checkpoint["image_size"]),
            transforms.ToTensor(),
            transforms.Normalize(
                tuple(checkpoint["mean"]),
                tuple(checkpoint["std"]),
            ),
        ]
    )
    return _LoadedClassifier(
        model=model,
        preprocessing=preprocessing,
        class_names=class_names,
        device=device,
        image_module=Image,
        torch_module=torch,
    )


def _get_classifier() -> _LoadedClassifier:
    global _loaded_classifier
    with _classifier_lock:
        if _loaded_classifier is None:
            _loaded_classifier = _load_classifier()
        return _loaded_classifier


def classify_image(image_path: Path) -> ClassificationResult:
    classifier = _get_classifier()
    image_module = classifier.image_module
    try:
        with image_module.open(image_path) as image:
            image_tensor = (
                classifier.preprocessing(image.convert("RGB"))
                .unsqueeze(0)
                .to(classifier.device)
            )
    except (
        OSError,
        ValueError,
        image_module.DecompressionBombError,
    ) as exc:
        raise InvalidImageError(f"Unable to read a valid image: {image_path}") from exc

    with classifier.torch_module.inference_mode():
        probabilities = (
            classifier.torch_module.softmax(
                classifier.model(image_tensor)[0],
                dim=0,
            )
            .cpu()
            .tolist()
        )

    predicted_index = max(
        range(len(probabilities)),
        key=probabilities.__getitem__,
    )
    return ClassificationResult(
        predicted_class=classifier.class_names[predicted_index],
        confidence=probabilities[predicted_index],
        probabilities=dict(zip(classifier.class_names, probabilities)),
        device=str(classifier.device),
    )
