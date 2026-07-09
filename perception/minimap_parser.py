"""Minimap Parser — detect hero positions on the LOL minimap.

Uses a combination of:
1. Color segmentation for red/green indicators
2. Contour-based circular blob detection for hero icons
3. Adaptive thresholding for robust detection

Works for both live game and replay videos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np
from numpy.typing import NDArray


@dataclass
class MinimapDetection:
    """A hero detected on the minimap."""
    x: int
    y: int
    team: str  # "ally" or "enemy"
    radius: int = 3
    color_tag: str = ""


class MinimapParser:
    """Detect hero positions on the LOL minimap.

    Strategy: detect bright circular blobs on the dark minimap background.
    Red-tinted circles = enemies, green-tinted circles = allies.
    Also detects via contour shape (hero icons are roughly circular).

    Args:
        min_radius: Minimum blob radius to keep.
        max_radius: Maximum blob radius to keep.
    """

    def __init__(
        self,
        min_radius: int = 4,
        max_radius: int = 16,
    ) -> None:
        self._min_radius = min_radius
        self._max_radius = max_radius

    def parse(self, minimap_roi: NDArray[np.uint8]) -> List[MinimapDetection]:
        """Detect hero icons on the minimap.

        Args:
            minimap_roi: Cropped minimap image (BGR, typically ~300-400px).

        Returns:
            List of MinimapDetection objects.
        """
        if minimap_roi is None or minimap_roi.size == 0:
            return []

        hsv = cv2.cvtColor(minimap_roi, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(minimap_roi, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        detections: List[MinimapDetection] = []

        # Strategy 1: Detect bright colored regions (hero indicators)
        # Red indicators (enemy)
        red_mask1 = cv2.inRange(hsv, (0, 80, 160), (15, 255, 255))
        red_mask2 = cv2.inRange(hsv, (165, 80, 160), (180, 255, 255))
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)

        # Green indicators (ally)
        green_mask = cv2.inRange(hsv, (30, 80, 160), (80, 255, 255))

        # Combine and find blobs
        for mask, team, color in [(red_mask, "enemy", "red"), (green_mask, "ally", "green")]:
            circles = self._find_blobs(mask, minimap_roi)
            for cx, cy, r in circles:
                detections.append(
                    MinimapDetection(x=cx, y=cy, team=team, radius=r, color_tag=color)
                )

        # Strategy 2: Hough circle detection — only if Strategy 1 found < 3
        if len(detections) < 3:
            gray = cv2.cvtColor(minimap_roi, cv2.COLOR_BGR2GRAY)
            remaining_circles = self._find_circles_hough(gray, minimap_roi)
            already_detected = set()
            for d in detections:
                already_detected.add((d.x // 15, d.y // 15))

            for cx, cy, r in remaining_circles:
                grid_key = (cx // 15, cy // 15)
                if grid_key not in already_detected:
                    team = self._classify_team(hsv, cx, cy)
                    if team:
                        detections.append(
                            MinimapDetection(x=cx, y=cy, team=team, radius=r, color_tag=f"bright_{team}")
                        )
                        already_detected.add(grid_key)

        # Dedup: merge overlapping detections
        detections = self._nms(detections, threshold=20)

        return detections

    def _find_blobs(self, mask: NDArray, roi: NDArray) -> List[Tuple[int, int, int]]:
        """Find circular blobs in a binary mask."""
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        circles = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 10:
                continue
            (cx, cy), radius = cv2.minEnclosingCircle(cnt)
            cx, cy, radius = int(cx), int(cy), int(radius)

            if self._min_radius <= radius <= self._max_radius:
                circularity = area / (np.pi * radius * radius + 1e-6)
                if circularity > 0.25:
                    circles.append((cx, cy, radius))

        return circles

    def _find_circles_hough(
        self, gray: NDArray, roi: NDArray
    ) -> List[Tuple[int, int, int]]:
        """Use HoughCircles to find circular shapes."""
        # Pre-process
        blurred = cv2.GaussianBlur(gray, (5, 5), 1.5)

        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=15,
            param1=80,
            param2=25,
            minRadius=self._min_radius,
            maxRadius=self._max_radius,
        )

        if circles is None:
            return []

        results = []
        for x, y, r in circles[0]:
            results.append((int(x), int(y), int(r)))
        return results

    def _classify_team(self, hsv: NDArray, cx: int, cy: int) -> Optional[str]:
        """Classify a circle as ally/enemy by checking local color."""
        h, w = hsv.shape[:2]
        r = 10
        x1, x2 = max(0, cx - r), min(w, cx + r)
        y1, y2 = max(0, cy - r), min(h, cy + r)
        patch = hsv[y1:y2, x1:x2]
        if patch.size == 0:
            return None

        red1 = np.sum((patch[:, :, 0] < 15) & (patch[:, :, 1] > 80) & (patch[:, :, 2] > 150))
        red2 = np.sum((patch[:, :, 0] > 165) & (patch[:, :, 1] > 80) & (patch[:, :, 2] > 150))
        red_total = red1 + red2
        green = np.sum((patch[:, :, 0] > 30) & (patch[:, :, 0] < 80) & (patch[:, :, 1] > 80) & (patch[:, :, 2] > 150))

        if red_total > green and red_total > 3:
            return "enemy"
        elif green > red_total and green > 3:
            return "ally"
        return None

    @staticmethod
    def _nms(detections: List[MinimapDetection], threshold: int = 20) -> List[MinimapDetection]:
        """Remove overlapping detections (keep the one with larger radius)."""
        if not detections:
            return []

        # Sort by radius descending (prefer larger circles)
        sorted_dets = sorted(detections, key=lambda d: d.radius, reverse=True)
        keep = []
        for d in sorted_dets:
            too_close = False
            for k in keep:
                dist = ((d.x - k.x) ** 2 + (d.y - k.y) ** 2) ** 0.5
                if dist < threshold:
                    too_close = True
                    break
            if not too_close:
                keep.append(d)
        return keep

    def annotate(
        self, minimap_roi: NDArray[np.uint8], detections: List[MinimapDetection]
    ) -> NDArray[np.uint8]:
        """Draw detections on minimap for visualization."""
        vis = minimap_roi.copy()
        for det in detections:
            color = (0, 0, 255) if det.team == "enemy" else (0, 255, 0)
            cv2.circle(vis, (det.x, det.y), det.radius + 3, color, 2)
            cv2.putText(
                vis, det.team[0].upper(),
                (det.x - 5, det.y - det.radius - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1,
            )
        return vis
