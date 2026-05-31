"""Train YOLO models from VOC-converted dataset.

Usage:
    python scripts/train_yolo.py --data data/yolo_dataset/dataset.yaml --model yolov8m --epochs 100
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


def train(
    data_yaml: str | Path,
    model_size: str = "yolov8m",
    epochs: int = 100,
    imgsz: int = 960,
    batch: int = 8,
    device: str = "0",
    project: str = "runs/train",
    name: str = "lol_yolo",
    resume: bool = False,
) -> None:
    """Train a YOLO model.

    Args:
        data_yaml: Path to dataset YAML config.
        model_size: YOLO model variant (yolov8n/s/m/l/x).
        epochs: Training epochs.
        imgsz: Input image size.
        batch: Batch size (reduce if OOM).
        device: CUDA device.
        project: Output project directory.
        name: Experiment name.
        resume: Resume from last checkpoint.
    """
    model = YOLO(f"{model_size}.pt")

    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project=project,
        name=name,
        exist_ok=True,
        patience=20,
        save=True,
        save_period=10,
        verbose=True,
        resume=resume,
    )

    print(f"\nTraining complete. Results saved to: {project}/{name}")
    print(f"Best weights: {project}/{name}/weights/best.pt")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train YOLO model")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/yolo_dataset/dataset.yaml"),
        help="Path to dataset YAML",
    )
    parser.add_argument(
        "--model",
        default="yolov8m",
        choices=["yolov8n", "yolov8s", "yolov8m", "yolov8l", "yolov8x"],
        help="YOLO model variant",
    )
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="0")
    parser.add_argument("--name", default="lol_yolo")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    train(
        data_yaml=args.data,
        model_size=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        name=args.name,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
