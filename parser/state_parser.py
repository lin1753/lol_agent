"""State Parser — transforms YOLO detections + OCR results into GameState."""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from models.game_state import (
    GameState,
    HeroPosition,
    ObjectiveStatus,
    Team,
)
from perception.minimap_parser import MinimapDetection
from perception.yolo_infer import Detection


# Class name to category mapping
_HERO_CLASSES = {"green_hp_hero", "blue_hp_hero", "red_hp_hero"}
_HERO_HP_BAR_CLASSES = {"green_hp_bar", "blue_hp_bar", "red_hp_bar"}
_MINIMAP_CLASS = "minimap"
_ALLY_ICON_CLASS = "ally_hero_icon"
_ENEMY_ICON_CLASS = "enemy_hero_icon"
_OBJECTIVE_CLASSES = {
    "baron": "baron",
    "herald": "herald",
    "dragon": "dragon",
    "void_grub": "herald",
}
_TOWER_CLASSES = {"blue_tower", "red_tower"}
_PLAYER_HP_BAR = "player_hp_bar"
_PLAYER_LEVEL = "player_level"
_GOLD_CLASS = "gold"
_TIME_CLASS = "game_time"
_KDA_CLASS = "kda"


def _classify_hero_team(det: Detection) -> Team:
    """Infer hero team from detection class."""
    if det.class_name in ("green_hp_hero", "blue_hp_hero"):
        return Team.BLUE
    return Team.RED


def _estimate_lane(x: float, y: float, frame_w: int, frame_h: int) -> Optional[str]:
    """Rough lane estimation from position in center viewport."""
    # Normalized coordinates
    nx = x / frame_w
    ny = y / frame_h

    if ny < 0.33:
        return "top"
    elif ny > 0.66:
        return "bot"
    elif 0.33 <= ny <= 0.66 and 0.33 <= nx <= 0.66:
        return "mid"
    return "jungle"


def _count_teamfight_probability(heroes: List[HeroPosition]) -> float:
    """Estimate teamfight probability based on hero clustering."""
    if len(heroes) < 3:
        return 0.0

    # Count heroes within a cluster radius
    positions = [(h.x, h.y) for h in heroes]
    cluster_count = 0
    for i, (x1, y1) in enumerate(positions):
        nearby = sum(
            1
            for j, (x2, y2) in enumerate(positions)
            if i != j and ((x1 - x2) ** 2 + (y1 - y2) ** 2) < 10000
        )
        cluster_count = max(cluster_count, nearby)

    # 3+ heroes near each other = high probability
    if cluster_count >= 4:
        return 0.9
    elif cluster_count >= 3:
        return 0.6
    elif cluster_count >= 2:
        return 0.3
    return 0.1


class StateParser:
    """Convert raw YOLO detections and OCR results into a GameState.

    Optionally integrates StateEngine for state understanding.

    Usage:
        parser = StateParser()
        state = parser.parse(minimap_dets, hero_dets, ocr_results, frame_shape)
    """

    def __init__(self, enable_state_engine: bool = True):
        self._state_engine = None
        if enable_state_engine:
            from reasoning.state_engine import StateEngine
            self._state_engine = StateEngine()

    def parse(
        self,
        minimap_detections: List[Detection],
        hero_detections: List[Detection],
        ocr_results: Dict[str, str],
        frame_shape: tuple[int, int] = (1080, 1920),
    ) -> GameState:
        """Parse detections into a GameState.

        Args:
            minimap_detections: Detections from minimap ROI.
            hero_detections: Detections from center viewport ROI.
            ocr_results: Parsed OCR values {'time': '12:34', 'kda': '3/1/5', 'gold': '5500', 'level': '11'}.
            frame_shape: (height, width) of the full frame.

        Returns:
            GameState object.
        """
        fh, fw = frame_shape

        # Parse visible heroes from center viewport
        visible_enemies = []
        visible_allies = []
        for det in hero_detections:
            if det.class_name not in _HERO_CLASSES:
                continue
            team = _classify_hero_team(det)
            cx, cy = det.center
            lane = _estimate_lane(cx, cy, fw, fh)
            hp = HeroPosition(
                name=det.class_name,
                team=team,
                x=float(cx),
                y=float(cy),
                lane=lane,
            )
            if team == Team.RED:
                visible_enemies.append(hp)
            else:
                visible_allies.append(hp)

        # Parse minimap positions
        minimap_enemy = {}
        minimap_ally = {}
        for det in minimap_detections:
            if det.class_name == _ENEMY_ICON_CLASS:
                cx, cy = det.center
                minimap_enemy[f"enemy_{len(minimap_enemy)}"] = (float(cx), float(cy))
            elif det.class_name == _ALLY_ICON_CLASS:
                cx, cy = det.center
                minimap_ally[f"ally_{len(minimap_ally)}"] = (float(cx), float(cy))

        # Parse objectives from minimap
        dragon = ObjectiveStatus(alive=True)
        herald = ObjectiveStatus(alive=True)
        baron = ObjectiveStatus(alive=True)
        for det in minimap_detections:
            if det.class_name in _OBJECTIVE_CLASSES:
                obj_type = _OBJECTIVE_CLASSES[det.class_name]
                if obj_type == "dragon":
                    dragon = ObjectiveStatus(alive=True)
                elif obj_type == "herald":
                    herald = ObjectiveStatus(alive=True)
                elif obj_type == "baron":
                    baron = ObjectiveStatus(alive=True)

        # Parse towers
        blue_towers = sum(
            1 for d in minimap_detections if d.class_name == "blue_tower"
        )
        red_towers = sum(
            1 for d in minimap_detections if d.class_name == "red_tower"
        )

        # Parse OCR values
        current_time = self._parse_time(ocr_results.get("time", ""))
        kills, deaths, assists = self._parse_kda(ocr_results.get("kda", ""))
        gold = self._parse_int(ocr_results.get("gold", "0"))
        level = self._parse_int(ocr_results.get("level", "1"))

        # Infer danger lane
        danger_lane = self._infer_danger_lane(minimap_enemy, minimap_ally)

        # Teamfight probability
        all_heroes = visible_enemies + visible_allies
        teamfight_prob = _count_teamfight_probability(all_heroes)

        return GameState(
            current_time=current_time,
            visible_enemies=visible_enemies,
            visible_allies=visible_allies,
            minimap_enemy_positions=minimap_enemy,
            minimap_ally_positions=minimap_ally,
            dragon=dragon,
            herald=herald,
            baron=baron,
            current_gold=gold,
            player_level=level,
            kills=kills,
            deaths=deaths,
            assists=assists,
            danger_lane=danger_lane,
            teamfight_probability=teamfight_prob,
            blue_towers_alive=blue_towers,
            red_towers_alive=red_towers,
        )

    def parse_with_minimap(
        self,
        hero_detections: List[Detection],
        minimap_detections: List[MinimapDetection],
        ocr_results: Dict[str, str],
        frame_shape: tuple[int, int] = (1080, 1920),
    ) -> GameState:
        """Parse with minimap_parser (OpenCV) instead of YOLO minimap detections.

        Args:
            hero_detections: YOLO detections from center viewport.
            minimap_detections: MinimapDetection from OpenCV minimap parser.
            ocr_results: OCR values dict.
            frame_shape: (height, width).

        Returns:
            GameState object.
        """
        fh, fw = frame_shape

        # Parse visible heroes from center YOLO
        visible_enemies = []
        visible_allies = []
        for det in hero_detections:
            if det.class_name not in _HERO_CLASSES:
                continue
            team = _classify_hero_team(det)
            cx, cy = det.center
            lane = _estimate_lane(cx, cy, fw, fh)
            hp = HeroPosition(
                name=det.class_name, team=team,
                x=float(cx), y=float(cy), lane=lane,
            )
            if team == Team.RED:
                visible_enemies.append(hp)
            else:
                visible_allies.append(hp)

        # Parse minimap positions from OpenCV detections
        minimap_enemy = {}
        minimap_ally = {}
        for det in minimap_detections:
            key = f"{det.team}_{len(minimap_enemy if det.team == 'enemy' else minimap_ally)}"
            pos = (float(det.x), float(det.y))
            if det.team == "enemy":
                minimap_enemy[key] = pos
            else:
                minimap_ally[key] = pos

        # OCR
        current_time = self._parse_time(ocr_results.get("time", ""))
        kills, deaths, assists = self._parse_kda(ocr_results.get("kda", ""))
        gold = self._parse_int(ocr_results.get("gold", "0"))
        level = self._parse_int(ocr_results.get("level", "1"))

        # Infer danger lane from minimap enemy positions
        danger_lane = self._infer_danger_lane(minimap_enemy, minimap_ally)

        all_heroes = visible_enemies + visible_allies
        teamfight_prob = _count_teamfight_probability(all_heroes)

        state = GameState(
            current_time=current_time,
            visible_enemies=visible_enemies,
            visible_allies=visible_allies,
            minimap_enemy_positions=minimap_enemy,
            minimap_ally_positions=minimap_ally,
            current_gold=gold,
            player_level=level,
            kills=kills,
            deaths=deaths,
            assists=assists,
            danger_lane=danger_lane,
            teamfight_probability=teamfight_prob,
        )

        return state

    def enrich_state(
        self, state: GameState, memory: "TemporalMemory"
    ) -> GameState:
        """Apply StateEngine to enrich GameState with phase/context/combat/threat.

        Call this after parse_with_minimap and after updating memory.
        """
        if self._state_engine:
            state = self._state_engine.understand(state, memory)
        return state

    @staticmethod
    def _parse_time(time_str: str) -> float:
        """Convert MM:SS to seconds."""
        if not time_str:
            return 0.0
        parts = time_str.split(":")
        if len(parts) == 2:
            try:
                return int(parts[0]) * 60 + int(parts[1])
            except ValueError:
                return 0.0
        return 0.0

    @staticmethod
    def _parse_kda(kda_str: str) -> tuple[int, int, int]:
        """Parse K/D/A string."""
        if not kda_str:
            return (0, 0, 0)
        parts = kda_str.replace(" ", "").split("/")
        if len(parts) == 3:
            try:
                return (int(parts[0]), int(parts[1]), int(parts[2]))
            except ValueError:
                return (0, 0, 0)
        return (0, 0, 0)

    @staticmethod
    def _parse_int(s: str) -> int:
        """Parse integer from string, default 0."""
        try:
            return int(s.replace(",", "").replace(" ", ""))
        except (ValueError, AttributeError):
            return 0

    @staticmethod
    def _infer_danger_lane(
        enemy_pos: Dict[str, tuple[float, float]],
        ally_pos: Dict[str, tuple[float, float]],
    ) -> Optional[str]:
        """Infer which lane is most dangerous based on enemy concentration."""
        if not enemy_pos:
            return None

        # Count enemies by rough lane zones
        lane_counts = {"top": 0, "mid": 0, "bot": 0}
        for _, (_, y) in enemy_pos.items():
            if y < 360:
                lane_counts["top"] += 1
            elif y > 720:
                lane_counts["bot"] += 1
            else:
                lane_counts["mid"] += 1

        max_lane = max(lane_counts, key=lane_counts.get)
        if lane_counts[max_lane] >= 2:
            return max_lane
        return None
