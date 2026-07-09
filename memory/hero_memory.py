"""Hero Memory V2 — tracks per-hero last-seen state.

Replaces the hero-tracking portion of V1 TemporalMemory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from perception.minimap_parser import MinimapDetection
from utils.map import classify_lane


@dataclass
class HeroRecord:
    """Historical record for a single hero."""
    name: str
    team: str  # "ally" or "enemy"
    last_seen_time: float = 0.0
    last_x: float = 0.0
    last_y: float = 0.0
    last_lane: str = ""
    missing_duration: float = 0.0
    trajectory: list[tuple[float, float, float]] = field(default_factory=list)  # (time, x, y)


class HeroMemoryV2:
    """Tracks per-hero last-seen state from minimap detections.

    Usage:
        mem = HeroMemoryV2()
        mem.update(minimap_dets, current_time)
        missing = mem.get_missing_enemies()
    """

    def __init__(self) -> None:
        self._heroes: Dict[str, HeroRecord] = {}
        self._current_time: float = 0.0
        self._enemy_counter: int = 0
        self._ally_counter: int = 0

    def update(self, detections: List[MinimapDetection], current_time: float) -> None:
        """Update hero memory from minimap detections.

        Args:
            detections: List of MinimapDetection from OpenCV minimap parser.
            current_time: Current game time in seconds.
        """
        self._current_time = current_time
        seen_this_frame = set()

        for det in detections:
            key = self._get_or_create_key(det)
            seen_this_frame.add(key)
            record = self._heroes[key]
            record.last_seen_time = current_time
            record.last_x = float(det.x)
            record.last_y = float(det.y)
            record.last_lane = classify_lane(det.x / 240, det.y / 240)  # default minimap 240x240
            record.missing_duration = 0.0
            record.trajectory.append((current_time, float(det.x), float(det.y)))
            if len(record.trajectory) > 100:
                record.trajectory = record.trajectory[-50:]

        # Update missing durations for all tracked heroes
        for key, record in self._heroes.items():
            if key not in seen_this_frame and record.last_seen_time > 0:
                record.missing_duration = current_time - record.last_seen_time

    def get_missing_enemies(self) -> List[dict]:
        """Get all currently missing enemies with their missing duration.

        Returns:
            List of dicts sorted by missing duration (longest first).
        """
        missing = []
        for name, record in self._heroes.items():
            if record.team == "enemy" and record.missing_duration > 0:
                missing.append({
                    "name": name,
                    "missing_seconds": record.missing_duration,
                    "last_lane": record.last_lane,
                    "last_position": (record.last_x, record.last_y),
                })
        missing.sort(key=lambda x: x["missing_seconds"], reverse=True)
        return missing

    def get_jungler_missing_duration(self) -> float:
        """Get how long the enemy jungler has been missing.

        Heuristic: enemy missing longest from any lane.
        """
        max_missing = 0.0
        for _, record in self._heroes.items():
            if record.team == "enemy" and record.missing_duration > max_missing:
                max_missing = record.missing_duration
        return max_missing

    def get_hero_record(self, name: str) -> Optional[HeroRecord]:
        """Get record for a specific hero."""
        return self._heroes.get(name)

    def get_all_tracked(self) -> Dict[str, HeroRecord]:
        """Get all tracked heroes."""
        return dict(self._heroes)

    def clear(self) -> None:
        """Reset all memory."""
        self._heroes.clear()
        self._current_time = 0.0
        self._enemy_counter = 0
        self._ally_counter = 0

    def _get_or_create_key(self, det: MinimapDetection) -> str:
        """Get or create a stable key for a detection."""
        # Try to match existing hero by proximity
        best_key = None
        best_dist = 30.0  # max matching radius

        for key, record in self._heroes.items():
            if record.team != det.team:
                continue
            dist = ((record.last_x - det.x) ** 2 + (record.last_y - det.y) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_key = key

        if best_key is not None:
            return best_key

        # Create new entry
        if det.team == "enemy":
            self._enemy_counter += 1
            key = f"enemy_{self._enemy_counter}"
        else:
            self._ally_counter += 1
            key = f"ally_{self._ally_counter}"

        self._heroes[key] = HeroRecord(name=key, team=det.team)
        return key
