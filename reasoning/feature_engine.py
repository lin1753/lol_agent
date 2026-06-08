"""Feature Engine — extracts high-value game features from detections.

Transforms DetectionSummary + OCR results + minimap detections
into a FeatureBundle (6 Features).
"""

from __future__ import annotations

from typing import List

from perception.detection_summary import DetectionSummary
from perception.minimap_parser import MinimapDetection
from schemas.economy import EconomyFeature
from schemas.feature_bundle import FeatureBundle
from schemas.hero import HeroFeature
from schemas.map import MapFeature
from schemas.objective import ObjectiveFeature
from schemas.skill import SkillFeature
from schemas.wave import WaveFeature


# Minimap Y thresholds for lane classification (normalized to 0-1 range)
# Minimap is roughly 240x240 in the standard 1920x1080 layout
_LANE_Y_TOP_MAX = 0.33
_LANE_Y_BOT_MIN = 0.66

# Skill class name to field mapping
_SKILL_MAP = {
    "q_skill": "q_ready",
    "w_skill": "w_ready",
    "e_skill": "e_ready",
    "r_skill": "r_ready",
    "d_skill": "d_ready",
    "f_skill": "f_ready",
}

# Objective class name to field mapping
_OBJECTIVE_MAP = {
    "dragon": "dragon_alive",
    "void_grub": "grub_alive",
    "herald": "herald_alive",
    "baron": "baron_alive",
}


class FeatureEngine:
    """Extract 6 Features from detection results.

    Usage:
        engine = FeatureEngine()
        bundle = engine.extract(det_summary, ocr_results, minimap_dets, minimap_shape)
    """

    def extract(
        self,
        det_summary: DetectionSummary,
        ocr_results: dict[str, str],
        minimap_detections: List[MinimapDetection],
        minimap_shape: tuple[int, int] = (240, 240),
    ) -> FeatureBundle:
        """Extract all features from a single frame.

        Args:
            det_summary: Structured YOLO detection summary.
            ocr_results: OCR values dict (time, kda, gold, level).
            minimap_detections: Minimap hero positions from OpenCV parser.
            minimap_shape: (height, width) of the minimap region.

        Returns:
            FeatureBundle with all 6 features populated.
        """
        return FeatureBundle(
            hero=self._extract_hero(det_summary),
            economy=self._extract_economy(ocr_results),
            skill=self._extract_skill(det_summary),
            wave=self._extract_wave(det_summary),
            objective=self._extract_objective(det_summary),
            map=self._extract_map(minimap_detections, minimap_shape),
        )

    @staticmethod
    def _extract_hero(det_summary: DetectionSummary) -> HeroFeature:
        """Extract hero features from HP bar detections."""
        ally_bars = det_summary.ally_hp_bars
        enemy_bars = det_summary.enemy_hp_bars

        ally_count = len(ally_bars)
        enemy_count = len(enemy_bars)

        # HP proxy: area of HP bar (larger = more HP)
        ally_hp_total = sum(d.area for d in ally_bars)
        enemy_hp_total = sum(d.area for d in enemy_bars)

        ally_hp_avg = ally_hp_total / ally_count if ally_count > 0 else 0.0
        enemy_hp_avg = enemy_hp_total / enemy_count if enemy_count > 0 else 0.0

        return HeroFeature(
            ally_count=ally_count,
            enemy_count=enemy_count,
            ally_hp_avg=ally_hp_avg,
            enemy_hp_avg=enemy_hp_avg,
            ally_hp_total=ally_hp_total,
            enemy_hp_total=enemy_hp_total,
            visible_allies=len(det_summary.visible_allies),
            visible_enemies=len(det_summary.visible_enemies),
        )

    @staticmethod
    def _extract_economy(ocr_results: dict[str, str]) -> EconomyFeature:
        """Extract economy features from OCR results."""
        kills, deaths, assists = _parse_kda(ocr_results.get("kda", ""))
        gold = _parse_int(ocr_results.get("gold", "0"))
        level = _parse_int(ocr_results.get("level", "1"))

        return EconomyFeature(
            player_level=max(1, level),
            player_gold=max(0, gold),
            kills=kills,
            deaths=deaths,
            assists=assists,
        )

    @staticmethod
    def _extract_skill(det_summary: DetectionSummary) -> SkillFeature:
        """Extract skill readiness from skill detections.

        Default: all skills on CD (False).
        Only mark ready if YOLO detects the skill icon with high confidence.
        Skills with countdown numbers overlay = not detected = CD.
        """
        SKILL_CONFIDENCE_THRESHOLD = 0.7
        ready = {}
        for skill_state in det_summary.skills:
            if skill_state.confidence < SKILL_CONFIDENCE_THRESHOLD:
                continue
            field = _SKILL_MAP.get(skill_state.skill)
            if field:
                ready[field] = True

        return SkillFeature(**ready)

    @staticmethod
    def _extract_wave(det_summary: DetectionSummary) -> WaveFeature:
        """Extract wave features from minion counts."""
        return WaveFeature(
            ally_minions=det_summary.blue_minions,
            enemy_minions=det_summary.red_minions,
            # Cannon counts not yet separately tracked in DetectionSummary
            ally_cannons=0,
            enemy_cannons=0,
        )

    @staticmethod
    def _extract_objective(det_summary: DetectionSummary) -> ObjectiveFeature:
        """Extract objective status from detections."""
        kwargs = {}
        for cls_name, field in _OBJECTIVE_MAP.items():
            kwargs[field] = det_summary.objectives.get(cls_name, False)
        return ObjectiveFeature(**kwargs)

    @staticmethod
    def _extract_map(
        minimap_detections: List[MinimapDetection],
        minimap_shape: tuple[int, int],
    ) -> MapFeature:
        """Extract map features from minimap hero positions."""
        mh, mw = minimap_shape
        enemy_top = 0
        enemy_mid = 0
        enemy_bot = 0

        for det in minimap_detections:
            if det.team != "enemy":
                continue
            # Normalize Y to 0-1 range
            y_norm = det.y / mh if mh > 0 else 0.5
            if y_norm < _LANE_Y_TOP_MAX:
                enemy_top += 1
            elif y_norm > _LANE_Y_BOT_MIN:
                enemy_bot += 1
            else:
                enemy_mid += 1

        # Missing = enemies not on minimap (requires hero count from HP bars, default 5)
        visible_enemy = enemy_top + enemy_mid + enemy_bot
        enemy_missing = max(0, 5 - visible_enemy)

        return MapFeature(
            enemy_top=enemy_top,
            enemy_mid=enemy_mid,
            enemy_bot=enemy_bot,
            enemy_missing=enemy_missing,
        )


# --- Helper functions (same as StateParser) ---


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


def _parse_int(s: str) -> int:
    """Parse integer from string, default 0."""
    try:
        return int(s.replace(",", "").replace(" ", ""))
    except (ValueError, AttributeError):
        return 0
