from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torchvision import models, transforms


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify a single image with a trained disaster classifier.")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.checkpoint.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {args.checkpoint}")
    if not args.image.is_file():
        raise FileNotFoundError(f"Image not found: {args.image}")
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable in this PyTorch environment.")
    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available() else "cpu")
    if args.device == "cuda":
        device = torch.device("cuda")

    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=True)
    classes = checkpoint["class_names"]
    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(classes))
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device).eval()

    preprocessing = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(checkpoint["image_size"]),
        transforms.ToTensor(),
        transforms.Normalize(tuple(checkpoint["mean"]), tuple(checkpoint["std"])),
    ])
    with Image.open(args.image) as image:
        image_tensor = preprocessing(image.convert("RGB")).unsqueeze(0).to(device)
    with torch.inference_mode():
        probabilities = torch.softmax(model(image_tensor)[0], dim=0).cpu().tolist()

    predicted_index = max(range(len(probabilities)), key=probabilities.__getitem__)
    print(json.dumps({
        "image": str(args.image.resolve()),
        "predicted_class": classes[predicted_index],
        "confidence": probabilities[predicted_index],
        "probabilities": dict(zip(classes, probabilities)),
        "note": "Image-level prediction; confidence is not calibrated and is not a verified damage assessment.",
    }, indent=2))


if __name__ == "__main__":
    main()
