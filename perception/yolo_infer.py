"""YOLO inference module supporting multiple models (minimap/hero/etc.)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import torch
from numpy.typing import NDArray
from ultralytics import YOLO


@dataclass
class Detection:
    """A single object detection result."""

    class_id: int
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)

    @property
    def center(self) -> tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def area(self) -> int:
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)


class YoloInfer:
    """Multi-model YOLO inference engine.

    Supports loading multiple named models (e.g. 'minimap', 'hero')
    and running inference on numpy images.

    Args:
        device: CUDA device string ('0', 'cuda:0', 'cpu').
        use_fp16: Enable FP16 inference (requires CUDA).
    """

    def __init__(
        self,
        device: str = "0",
        use_fp16: bool = True,
    ) -> None:
        self._device = device
        self._use_fp16 = use_fp16 and torch.cuda.is_available()
        self._models: Dict[str, YOLO] = {}
        self._class_names: Dict[str, Dict[int, str]] = {}

    def load_model(
        self,
        name: str,
        weights_path: str | Path,
    ) -> None:
        """Load a YOLO model and register it under a name.

        Args:
            name: Model identifier (e.g. 'minimap', 'hero').
            weights_path: Path to .pt weights file.
        """
        model = YOLO(str(weights_path))
        device = f"cuda:{self._device}" if self._device.isdigit() else self._device
        model.to(device)
        if self._use_fp16:
            model.model.half()
        self._models[name] = model
        # Cache class names
        self._class_names[name] = model.names
        print(f"Loaded model '{name}' from {weights_path} on {self._device}")

    def predict(
        self,
        model_name: str,
        image: NDArray[np.uint8],
        conf: float = 0.25,
        iou: float = 0.45,
    ) -> List[Detection]:
        """Run inference with a named model.

        Args:
            model_name: Name of the loaded model.
            image: Input image as numpy array (H x W x C, BGR).
            conf: Confidence threshold.
            iou: NMS IoU threshold.

        Returns:
            List of Detection objects.
        """
        if model_name not in self._models:
            raise ValueError(
                f"Model '{model_name}' not loaded. "
                f"Available: {list(self._models.keys())}"
            )

        model = self._models[model_name]
        names = self._class_names[model_name]

        results = model.predict(
            source=image,
            conf=conf,
            iou=iou,
            verbose=False,
            half=self._use_fp16,
        )

        detections = []
        for result in results:
            if result.boxes is None:
                continue
            boxes = result.boxes
            for i in range(len(boxes)):
                xyxy = boxes.xyxy[i].cpu().numpy().astype(int)
                conf_val = float(boxes.conf[i].cpu())
                cls_id = int(boxes.cls[i].cpu())
                detections.append(
                    Detection(
                        class_id=cls_id,
                        class_name=names.get(cls_id, str(cls_id)),
                        confidence=conf_val,
                        x1=int(xyxy[0]),
                        y1=int(xyxy[1]),
                        x2=int(xyxy[2]),
                        y2=int(xyxy[3]),
                    )
                )

        return detections

    def predict_all(
        self,
        image: NDArray[np.uint8],
        conf: float = 0.25,
        iou: float = 0.45,
    ) -> Dict[str, List[Detection]]:
        """Run inference with all loaded models.

        Returns:
            Dict mapping model name to its detection list.
        """
        return {
            name: self.predict(name, image, conf, iou)
            for name in self._models
        }

    @property
    def model_names(self) -> list[str]:
        return list(self._models.keys())

    def get_class_names(self, model_name: str) -> Dict[int, str]:
        return self._class_names[model_name]
