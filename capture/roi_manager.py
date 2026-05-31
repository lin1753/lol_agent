"""ROI Manager — crop fixed UI regions from a full game frame."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class Region:
    """A rectangular region defined by top-left corner and size."""

    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h


class ROIManager:
    """Crop predefined UI regions from a 1920x1080 game frame.

    Args:
        config_path: Path to roi_config.json. If None, uses default regions.
    """

    # Default regions for 1920x1080 LOL UI
    DEFAULT_REGIONS: Dict[str, Region] = {
        "minimap": Region(0, 780, 300, 300),
        "topbar": Region(300, 0, 1300, 120),
        "center": Region(300, 200, 1300, 700),
        "hud": Region(500, 850, 900, 230),
    }

    def __init__(self, config_path: str | Path | None = None) -> None:
        if config_path is not None:
            self._regions = self._load_config(config_path)
        else:
            self._regions = dict(self.DEFAULT_REGIONS)

    @staticmethod
    def _load_config(path: str | Path) -> Dict[str, Region]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        regions = {}
        for name, rect in data["regions"].items():
            regions[name] = Region(
                x=rect["x"], y=rect["y"], w=rect["w"], h=rect["h"]
            )
        return regions

    @property
    def region_names(self) -> list[str]:
        return list(self._regions.keys())

    def get_region(self, name: str) -> Region:
        return self._regions[name]

    def crop(self, frame: NDArray[np.uint8], name: str) -> NDArray[np.uint8]:
        """Crop a named region from the frame.

        Args:
            frame: Full game frame (H x W x C).
            name: Region name (e.g. 'minimap', 'topbar', 'center', 'hud').

        Returns:
            Cropped numpy array.
        """
        r = self._regions[name]
        fh, fw = frame.shape[:2]
        # Scale region coordinates if frame size differs from 1920x1080
        sx = fw / 1920
        sy = fh / 1080
        x1 = int(r.x * sx)
        y1 = int(r.y * sy)
        x2 = int(r.x2 * sx)
        y2 = int(r.y2 * sy)
        return frame[y1:y2, x1:x2].copy()

    def crop_all(
        self, frame: NDArray[np.uint8]
    ) -> Dict[str, NDArray[np.uint8]]:
        """Crop all defined regions from the frame.

        Returns:
            Dict mapping region name to cropped numpy array.
        """
        return {name: self.crop(frame, name) for name in self._regions}
