from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

import torch
from PIL import Image, UnidentifiedImageError
from torch import nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, models, transforms


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train an EfficientNet-B0 disaster image classifier.")
    parser.add_argument("--data-dir", type=Path, required=True, help="Folder containing one subfolder per class.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "models" / "disaster_classifier" / "efficientnet_b0.pth",
        help="Output checkpoint path (excluded from Git by default).",
    )
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--learning-rate", type=float, default=5e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument("--test-fraction", type=float, default=0.15)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    return parser.parse_args()


def find_imagefolder_root(data_dir: Path) -> Path:
    root = data_dir.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Dataset directory does not exist: {root}")

    candidates = [root]
    candidates.extend(path for path in root.iterdir() if path.is_dir())
    for candidate in candidates:
        class_dirs = [path for path in candidate.iterdir() if path.is_dir()]
        usable_classes = [
            folder for folder in class_dirs
            if any(file.suffix.lower() in IMAGE_EXTENSIONS for file in folder.rglob("*") if file.is_file())
        ]
        if len(usable_classes) >= 2:
            return candidate
    raise ValueError(
        f"No image-folder dataset found under {root}. Expected one directory per class containing images."
    )


def stratified_indices(
    targets: list[int],
    validation_fraction: float,
    test_fraction: float,
    seed: int,
) -> tuple[list[int], list[int], list[int]]:
    if validation_fraction <= 0 or test_fraction <= 0 or validation_fraction + test_fraction >= 1:
        raise ValueError("Validation and test fractions must be positive and sum to less than 1.")

    by_class: dict[int, list[int]] = defaultdict(list)
    for index, target in enumerate(targets):
        by_class[target].append(index)

    rng = random.Random(seed)
    train_indices: list[int] = []
    validation_indices: list[int] = []
    test_indices: list[int] = []
    for class_id, indices in sorted(by_class.items()):
        if len(indices) < 3:
            raise ValueError(
                f"Class {class_id} has only {len(indices)} images; at least 3 are needed for train/validation/test."
            )
        rng.shuffle(indices)
        test_count = max(1, round(len(indices) * test_fraction))
        validation_count = max(1, round(len(indices) * validation_fraction))
        while test_count + validation_count >= len(indices):
            if test_count >= validation_count:
                test_count -= 1
            else:
                validation_count -= 1
        test_indices.extend(indices[:test_count])
        validation_indices.extend(indices[test_count:test_count + validation_count])
        train_indices.extend(indices[test_count + validation_count:])

    rng.shuffle(train_indices)
    rng.shuffle(validation_indices)
    rng.shuffle(test_indices)
    return train_indices, validation_indices, test_indices


def make_loaders(
    root: Path,
    image_size: int,
    batch_size: int,
    workers: int,
    validation_fraction: float,
    test_fraction: float,
    seed: int,
    device: torch.device,
) -> tuple[DataLoader, DataLoader, DataLoader, list[str], dict[str, int], list[str]]:
    train_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.RandomResizedCrop(image_size, scale=(0.75, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(12),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    evaluation_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(image_size),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])

    validation_cache: dict[str, bool] = {}
    invalid_images: list[str] = []

    def is_valid_image(path: str) -> bool:
        if path not in validation_cache:
            try:
                with Image.open(path) as image:
                    image.load()
            except (UnidentifiedImageError, OSError, SyntaxError):
                validation_cache[path] = False
                invalid_images.append(path)
            else:
                validation_cache[path] = True
        return validation_cache[path]

    base = datasets.ImageFolder(root, is_valid_file=is_valid_image)
    if len(base.classes) < 2:
        raise ValueError("At least two image classes are required.")
    train_indices, validation_indices, test_indices = stratified_indices(
        base.targets, validation_fraction, test_fraction, seed
    )

    train_dataset = Subset(
        datasets.ImageFolder(root, transform=train_transform, is_valid_file=is_valid_image),
        train_indices,
    )
    validation_dataset = Subset(
        datasets.ImageFolder(root, transform=evaluation_transform, is_valid_file=is_valid_image),
        validation_indices,
    )
    test_dataset = Subset(
        datasets.ImageFolder(root, transform=evaluation_transform, is_valid_file=is_valid_image),
        test_indices,
    )
    generator = torch.Generator().manual_seed(seed)
    common = {
        "batch_size": batch_size,
        "num_workers": workers,
        "pin_memory": device.type == "cuda",
        "persistent_workers": workers > 0,
    }
    train_loader = DataLoader(train_dataset, shuffle=True, generator=generator, **common)
    validation_loader = DataLoader(validation_dataset, shuffle=False, **common)
    test_loader = DataLoader(test_dataset, shuffle=False, **common)
    counts = {class_name: sum(target == index for target in base.targets) for index, class_name in enumerate(base.classes)}
    return train_loader, validation_loader, test_loader, base.classes, counts, invalid_images


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None = None,
    scaler: torch.amp.GradScaler | None = None,
) -> dict[str, float]:
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    correct = 0
    total = 0

    context = torch.enable_grad if training else torch.inference_mode
    with context():
        for images, labels in loader:
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            if training:
                optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
                logits = model(images)
                loss = criterion(logits, labels)
            if training:
                if scaler is not None and scaler.is_enabled():
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    loss.backward()
                    optimizer.step()
            batch_size = labels.size(0)
            total_loss += loss.item() * batch_size
            correct += (logits.argmax(dim=1) == labels).sum().item()
            total += batch_size

    return {"loss": total_loss / total, "accuracy": correct / total}


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    classes: list[str],
    device: torch.device,
) -> dict:
    model.eval()
    matrix = [[0 for _ in classes] for _ in classes]
    with torch.inference_mode():
        for images, labels in loader:
            images = images.to(device, non_blocking=True)
            predictions = model(images).argmax(dim=1).cpu().tolist()
            for actual, predicted in zip(labels.tolist(), predictions):
                matrix[actual][predicted] += 1

    per_class = {}
    for index, name in enumerate(classes):
        true_positive = matrix[index][index]
        support = sum(matrix[index])
        predicted_count = sum(row[index] for row in matrix)
        precision = true_positive / predicted_count if predicted_count else 0.0
        recall = true_positive / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[name] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }
    total = sum(sum(row) for row in matrix)
    correct = sum(matrix[index][index] for index in range(len(classes)))
    return {
        "accuracy": correct / total if total else 0.0,
        "confusion_matrix": matrix,
        "class_names": classes,
        "per_class": per_class,
        "sample_count": total,
    }


def main() -> None:
    args = parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.image_size < 32 or args.patience < 1:
        raise ValueError("Epochs, batch size, patience, and image size must be positive.")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable in this PyTorch environment.")
    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available() else "cpu")
    if args.device == "cuda":
        device = torch.device("cuda")

    dataset_root = find_imagefolder_root(args.data_dir)
    train_loader, validation_loader, test_loader, classes, class_counts, invalid_images = make_loaders(
        dataset_root,
        args.image_size,
        args.batch_size,
        args.workers,
        args.validation_fraction,
        args.test_fraction,
        args.seed,
        device,
    )
    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(classes))
    model.to(device)

    train_subset = train_loader.dataset
    train_targets = [train_subset.dataset.targets[index] for index in train_subset.indices]
    counts = torch.bincount(torch.tensor(train_targets), minlength=len(classes)).to(device=device, dtype=torch.float32)
    class_weights = counts.sum() / (len(classes) * counts)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", patience=2, factor=0.5)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    best_validation_loss = float("inf")
    best_epoch = 0
    stale_epochs = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"Dataset: {dataset_root}")
    print(f"Classes: {classes}")
    print(f"Class counts: {class_counts}")
    print(f"Excluded unreadable images: {len(invalid_images)}")
    for image_path in invalid_images:
        print(f"Unreadable image: {image_path}")
    print(f"Device: {device}")

    for epoch in range(1, args.epochs + 1):
        training = run_epoch(model, train_loader, criterion, device, optimizer, scaler)
        validation = run_epoch(model, validation_loader, criterion, device)
        scheduler.step(validation["loss"])
        print(
            f"Epoch {epoch}/{args.epochs} "
            f"train_loss={training['loss']:.4f} train_acc={training['accuracy']:.4f} "
            f"val_loss={validation['loss']:.4f} val_acc={validation['accuracy']:.4f}"
        )
        if validation["loss"] < best_validation_loss:
            best_validation_loss = validation["loss"]
            best_epoch = epoch
            stale_epochs = 0
            torch.save(
                {
                    "format_version": 1,
                    "architecture": "efficientnet_b0",
                    "model_state_dict": model.state_dict(),
                    "class_names": classes,
                    "image_size": args.image_size,
                    "mean": list(MEAN),
                    "std": list(STD),
                    "best_epoch": best_epoch,
                    "validation_metrics": validation,
                    "training_config": {
                        "seed": args.seed,
                        "epochs_requested": args.epochs,
                        "batch_size": args.batch_size,
                        "learning_rate": args.learning_rate,
                        "weight_decay": args.weight_decay,
                        "validation_fraction": args.validation_fraction,
                        "test_fraction": args.test_fraction,
                    },
                },
                args.output,
            )
        else:
            stale_epochs += 1
            if stale_epochs >= args.patience:
                print(f"Early stopping after {epoch} epochs.")
                break

    checkpoint = torch.load(args.output, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    test_metrics = evaluate(model, test_loader, classes, device)
    report_path = args.output.with_suffix(".metrics.json")
    report = {
        "dataset": str(dataset_root),
        "split_method": "stratified random image-level split; source/event grouping is unavailable",
        "class_counts": class_counts,
        "excluded_unreadable_images": invalid_images,
        "train_samples": len(train_loader.dataset),
        "validation_samples": len(validation_loader.dataset),
        "test_samples": len(test_loader.dataset),
        "device": str(device),
        "seed": args.seed,
        "best_epoch": best_epoch,
        "best_validation_loss": best_validation_loss,
        "test": test_metrics,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Best checkpoint: {args.output}")
    print(f"Test accuracy: {test_metrics['accuracy']:.4f}")
    print(f"Test metrics: {report_path}")


if __name__ == "__main__":
    main()
