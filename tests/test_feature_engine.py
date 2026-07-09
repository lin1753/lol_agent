"""Tests for Feature Engine (P1-T3)."""

import pytest

from perception.detection_summary import DetectionSummary, SkillState
from perception.minimap_parser import MinimapDetection
from perception.yolo_infer import Detection
from reasoning.feature_engine import FeatureEngine
from utils.parsing import parse_kda as _parse_kda, parse_int as _parse_int


class TestFeatureEngine:
    @pytest.fixture
    def engine(self):
        return FeatureEngine()

    def _det(self, cls, x1, y1, x2, y2, conf=0.9):
        return Detection(class_id=0, class_name=cls, confidence=conf,
                         x1=x1, y1=y1, x2=x2, y2=y2)

    def test_empty_input(self, engine):
        summary = DetectionSummary()
        bundle = engine.extract(summary, {}, [], (240, 240))
        assert bundle.hero.ally_count == 0
        assert bundle.hero.enemy_count == 0
        assert bundle.economy.player_level == 1
        assert bundle.economy.player_gold == 0
        assert bundle.skill.q_ready is False
        assert bundle.wave.ally_minions == 0
        assert bundle.objective.dragon_alive is False
        assert bundle.map.enemy_top == 0

    # --- Hero Feature ---

    def test_hero_hp_bars(self, engine):
        summary = DetectionSummary(
            ally_hp_bars=[
                self._det("green_hp_bar", 100, 100, 200, 110),   # area=1000
                self._det("blue_hp_bar", 300, 200, 420, 212),    # area=1440
            ],
            enemy_hp_bars=[
                self._det("red_hp_bar", 500, 300, 580, 308),    # area=640
            ],
        )
        bundle = engine.extract(summary, {}, [])
        assert bundle.hero.ally_count == 2
        assert bundle.hero.enemy_count == 1
        assert bundle.hero.ally_hp_total == 2440
        assert bundle.hero.enemy_hp_total == 640
        assert bundle.hero.ally_hp_avg == 1220.0
        assert bundle.hero.enemy_hp_avg == 640.0

    def test_hero_visible_counts(self, engine):
        summary = DetectionSummary(
            visible_allies=[
                self._det("green_hp_hero", 100, 100, 150, 120),
                self._det("blue_hp_hero", 200, 200, 250, 220),
            ],
            visible_enemies=[
                self._det("red_hp_hero", 500, 500, 550, 520),
            ],
        )
        bundle = engine.extract(summary, {}, [])
        assert bundle.hero.visible_allies == 2
        assert bundle.hero.visible_enemies == 1

    def test_hero_no_bars_zero_avg(self, engine):
        summary = DetectionSummary()
        bundle = engine.extract(summary, {}, [])
        assert bundle.hero.ally_hp_avg == 0.0
        assert bundle.hero.enemy_hp_avg == 0.0

    # --- Economy Feature ---

    def test_economy_from_ocr(self, engine):
        ocr = {"kda": "5/2/8", "gold": "12000", "level": "14"}
        bundle = engine.extract(DetectionSummary(), ocr, [])
        assert bundle.economy.kills == 5
        assert bundle.economy.deaths == 2
        assert bundle.economy.assists == 8
        assert bundle.economy.player_gold == 12000
        assert bundle.economy.player_level == 14

    def test_economy_empty_ocr(self, engine):
        bundle = engine.extract(DetectionSummary(), {}, [])
        assert bundle.economy.kills == 0
        assert bundle.economy.player_gold == 0
        assert bundle.economy.player_level == 1

    def test_economy_level_clamped_to_min_1(self, engine):
        ocr = {"level": "0"}
        bundle = engine.extract(DetectionSummary(), ocr, [])
        assert bundle.economy.player_level == 1

    # --- Skill Feature ---

    def test_skill_ready(self, engine):
        summary = DetectionSummary(
            skills=[
                SkillState(skill="q_skill", confidence=0.9, bbox=(0, 0, 10, 10)),
                SkillState(skill="r_skill", confidence=0.85, bbox=(0, 0, 10, 10)),
                SkillState(skill="d_skill", confidence=0.8, bbox=(0, 0, 10, 10)),
            ],
        )
        bundle = engine.extract(summary, {}, [])
        assert bundle.skill.q_ready is True
        assert bundle.skill.w_ready is False
        assert bundle.skill.e_ready is False
        assert bundle.skill.r_ready is True
        assert bundle.skill.d_ready is True
        assert bundle.skill.f_ready is False
        assert bundle.skill.ult_ready is True
        assert bundle.skill.flash_ready is True

    def test_skill_empty(self, engine):
        summary = DetectionSummary()
        bundle = engine.extract(summary, {}, [])
        assert bundle.skill.combat_ready is False
        assert bundle.skill.ult_ready is False

    # --- Wave Feature ---

    def test_wave_from_detections(self, engine):
        summary = DetectionSummary(blue_minions=6, red_minions=3)
        bundle = engine.extract(summary, {}, [])
        assert bundle.wave.ally_minions == 6
        assert bundle.wave.enemy_minions == 3
        assert bundle.wave.wave_strength > 0  # ally pushing

    def test_wave_empty(self, engine):
        summary = DetectionSummary()
        bundle = engine.extract(summary, {}, [])
        assert bundle.wave.ally_minions == 0
        assert bundle.wave.wave_strength == 0.0

    # --- Objective Feature ---

    def test_objective_detected(self, engine):
        summary = DetectionSummary(objectives={"dragon": True, "herald": True})
        bundle = engine.extract(summary, {}, [])
        assert bundle.objective.dragon_alive is True
        assert bundle.objective.herald_alive is True
        assert bundle.objective.baron_alive is False
        assert bundle.objective.grub_alive is False

    def test_objective_none_detected(self, engine):
        summary = DetectionSummary()
        bundle = engine.extract(summary, {}, [])
        assert bundle.objective.dragon_alive is False
        assert bundle.objective.baron_alive is False

    # --- Map Feature ---

    def test_map_enemy_positions(self, engine):
        minimap_dets = [
            MinimapDetection(x=100, y=30, team="enemy"),   # y_norm=0.125 → top
            MinimapDetection(x=100, y=120, team="enemy"),  # y_norm=0.5 → mid
            MinimapDetection(x=100, y=200, team="enemy"),  # y_norm=0.833 → bot
            MinimapDetection(x=50, y=50, team="ally"),     # ignored
        ]
        bundle = engine.extract(DetectionSummary(), {}, minimap_dets, (240, 240))
        assert bundle.map.enemy_top == 1
        assert bundle.map.enemy_mid == 1
        assert bundle.map.enemy_bot == 1
        assert bundle.map.enemy_visible_total == 3
        assert bundle.map.enemy_missing == 2  # 5 - 3

    def test_map_no_enemies_on_minimap(self, engine):
        bundle = engine.extract(DetectionSummary(), {}, [], (240, 240))
        assert bundle.map.enemy_top == 0
        assert bundle.map.enemy_missing == 5

    def test_map_all_enemies_visible(self, engine):
        minimap_dets = [
            MinimapDetection(x=50, y=50, team="enemy"),
            MinimapDetection(x=100, y=100, team="enemy"),
            MinimapDetection(x=150, y=150, team="enemy"),
            MinimapDetection(x=80, y=80, team="enemy"),
            MinimapDetection(x=120, y=120, team="enemy"),
        ]
        bundle = engine.extract(DetectionSummary(), {}, minimap_dets, (240, 240))
        assert bundle.map.enemy_missing == 0

    # --- Full integration ---

    def test_full_extract(self, engine):
        summary = DetectionSummary(
            ally_hp_bars=[self._det("green_hp_bar", 100, 100, 200, 110)],
            enemy_hp_bars=[self._det("red_hp_bar", 500, 300, 580, 308)],
            visible_enemies=[self._det("red_hp_hero", 500, 300, 550, 320)],
            visible_allies=[self._det("green_hp_hero", 100, 100, 150, 120)],
            blue_minions=5,
            red_minions=2,
            objectives={"dragon": True},
            skills=[
                SkillState(skill="q_skill", confidence=0.9, bbox=(0, 0, 10, 10)),
                SkillState(skill="w_skill", confidence=0.9, bbox=(0, 0, 10, 10)),
                SkillState(skill="e_skill", confidence=0.9, bbox=(0, 0, 10, 10)),
                SkillState(skill="r_skill", confidence=0.9, bbox=(0, 0, 10, 10)),
            ],
        )
        ocr = {"kda": "3/1/5", "gold": "8500", "level": "11"}
        minimap = [
            MinimapDetection(x=100, y=50, team="enemy"),
            MinimapDetection(x=150, y=200, team="enemy"),
            MinimapDetection(x=80, y=80, team="ally"),
        ]
        bundle = engine.extract(summary, ocr, minimap, (240, 240))

        assert bundle.hero.ally_count == 1
        assert bundle.hero.enemy_count == 1
        assert bundle.economy.kills == 3
        assert bundle.economy.player_gold == 8500
        assert bundle.economy.player_level == 11
        assert bundle.skill.combat_ready is True
        assert bundle.wave.ally_minions == 5
        assert bundle.objective.dragon_alive is True
        assert bundle.map.enemy_visible_total == 2
        assert bundle.map.enemy_missing == 3


class TestHelperFunctions:
    def test_parse_kda(self):
        assert _parse_kda("3/1/5") == (3, 1, 5)
        assert _parse_kda("0/0/0") == (0, 0, 0)
        assert _parse_kda("") == (0, 0, 0)
        assert _parse_kda("abc") == (0, 0, 0)
        assert _parse_kda("10 / 2 / 15") == (10, 2, 15)

    def test_parse_int(self):
        assert _parse_int("5500") == 5500
        assert _parse_int("1,234") == 1234
        assert _parse_int("") == 0
        assert _parse_int("abc") == 0
