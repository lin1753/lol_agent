"""Post-process YOLO 29-class detections into structured results.

Extracts OCR regions and structured game elements from detection list.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from numpy.typing import NDArray

from perception.yolo_infer import Detection


# Class name constants (must match training config)
UI_CLASSES = {"game_time", "kda", "gold", "player_hp_bar"}
HERO_CLASSES = {"green_hp_hero", "blue_hp_hero", "red_hp_hero"}
HP_BAR_CLASSES = {"green_hp_bar", "blue_hp_bar", "red_hp_bar"}
MINION_CLASSES = {"red_minion", "red_cannon", "blue_minion", "blue_cannon"}
TOWER_CLASSES = {"blue_tower", "red_tower"}
OBJECTIVE_CLASSES = {"baron", "herald", "void_grub", "dragon"}
SKILL_CLASSES = {"q_skill", "w_skill", "e_skill", "r_skill", "d_skill", "f_skill"}
MINIMAP_CLASSES = {"minimap", "minimap_fov"}


@dataclass
class OcrRegion:
    """An OCR region detected by YOLO."""
    class_name: str
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float

    @property
    def crop_box(self) -> tuple[int, int, int, int]:
        return self.bbox


@dataclass
class SkillState:
    """Skill state detected by YOLO."""
    skill: str
    confidence: float
    bbox: tuple[int, int, int, int]


@dataclass
class DetectionSummary:
    """Structured summary of all detections."""
    # OCR regions
    ocr_regions: dict[str, OcrRegion] = field(default_factory=dict)
    # Heroes
    visible_enemies: list[Detection] = field(default_factory=list)
    visible_allies: list[Detection] = field(default_factory=list)
    enemy_hp_bars: list[Detection] = field(default_factory=list)
    ally_hp_bars: list[Detection] = field(default_factory=list)
    # Minions
    red_minions: int = 0
    blue_minions: int = 0
    # Towers
    blue_towers: int = 0
    red_towers: int = 0
    # Objectives
    objectives: dict[str, bool] = field(default_factory=dict)
    # Skills
    skills: list[SkillState] = field(default_factory=list)
    # Minimap
    minimap_region: Optional[tuple[int, int, int, int]] = None


def summarize_detections(
    detections: list[Detection],
    frame: Optional[NDArray[np.uint8]] = None,
) -> DetectionSummary:
    """Summarize YOLO detections into structured results.

    Args:
        detections: Raw YOLO detection list.
        frame: Optional frame for cropping OCR regions.

    Returns:
        DetectionSummary with organized results.
    """
    summary = DetectionSummary()

    for det in detections:
        cls = det.class_name
        bbox = det.bbox

        # UI elements → OCR regions
        if cls in UI_CLASSES:
            summary.ocr_regions[cls] = OcrRegion(
                class_name=cls, bbox=bbox, confidence=det.confidence
            )

        # Hero HP bars → team classification
        elif cls in HERO_CLASSES:
            if cls in ("green_hp_hero", "blue_hp_hero"):
                summary.visible_allies.append(det)
            else:
                summary.visible_enemies.append(det)

        # Colored HP bars (UI element)
        elif cls in HP_BAR_CLASSES:
            if cls in ("green_hp_bar", "blue_hp_bar"):
                summary.ally_hp_bars.append(det)
            else:
                summary.enemy_hp_bars.append(det)

        # Minions
        elif cls in MINION_CLASSES:
            if cls in ("red_minion", "red_cannon"):
                summary.red_minions += 1
            else:
                summary.blue_minions += 1

        # Towers
        elif cls in TOWER_CLASSES:
            if cls == "blue_tower":
                summary.blue_towers += 1
            else:
                summary.red_towers += 1

        # Objectives
        elif cls in OBJECTIVE_CLASSES:
            summary.objectives[cls] = True

        # Skills
        elif cls in SKILL_CLASSES:
            summary.skills.append(SkillState(
                skill=cls, confidence=det.confidence, bbox=bbox
            ))

        # Minimap
        elif cls in MINIMAP_CLASSES:
            summary.minimap_region = bbox

    return summary


def extract_ocr_regions(
    frame: NDArray[np.uint8],
    summary: DetectionSummary,
    scale: int = 4,
    padding: int = 5,
) -> dict[str, NDArray[np.uint8]]:
    """Crop and upscale OCR regions from the frame.

    Args:
        frame: Full game frame.
        summary: DetectionSummary with ocr_regions.
        scale: Upscale factor for better OCR accuracy.
        padding: Extra pixels around bbox for context.

    Returns:
        Dict mapping class name to cropped+upscaled image.
    """
    h, w = frame.shape[:2]
    crops = {}

    for cls_name, ocr_region in summary.ocr_regions.items():
        x1, y1, x2, y2 = ocr_region.bbox
        # Add padding and clamp to frame bounds
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(w, x2 + padding)
        y2 = min(h, y2 + padding)

        if x2 > x1 and y2 > y1:
            crop = frame[y1:y2, x1:x2]
            if scale > 1:
                crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            crops[cls_name] = crop

    return crops
