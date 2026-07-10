"""Tests for V2.0 Pydantic Schemas (P1-T1)."""

import json

import pytest

from schemas.hero import HeroFeature
from schemas.economy import EconomyFeature
from schemas.skill import SkillFeature
from schemas.wave import WaveFeature
from schemas.objective import ObjectiveFeature
from schemas.map import MapFeature


class TestHeroFeature:
    def test_defaults(self):
        f = HeroFeature()
        assert f.ally_count == 0
        assert f.enemy_count == 0
        assert f.ally_hp_avg == 0.0
        assert f.enemy_hp_avg == 0.0
        assert f.ally_hp_total == 0.0
        assert f.enemy_hp_total == 0.0
        assert f.visible_allies == 0
        assert f.visible_enemies == 0

    def test_custom_values(self):
        f = HeroFeature(
            ally_count=3, enemy_count=2,
            ally_hp_avg=75.5, enemy_hp_avg=40.0,
            ally_hp_total=226.5, enemy_hp_total=80.0,
            visible_allies=3, visible_enemies=2,
        )
        assert f.ally_count == 3
        assert f.enemy_count == 2
        assert f.ally_hp_avg == 75.5

    def test_json_roundtrip(self):
        f = HeroFeature(ally_count=2, enemy_count=1, ally_hp_avg=80.0)
        data = f.model_dump()
        f2 = HeroFeature.model_validate(data)
        assert f2 == f

    def test_validation_negative_rejected(self):
        with pytest.raises(Exception):
            HeroFeature(ally_count=-1)

    def test_validation_hp_range(self):
        with pytest.raises(Exception):
            HeroFeature(ally_hp_avg=-1.0)


class TestEconomyFeature:
    def test_defaults(self):
        f = EconomyFeature()
        assert f.player_level == 1
        assert f.player_gold == 0
        assert f.item_count == 0
        assert f.kills == 0
        assert f.deaths == 0
        assert f.assists == 0

    def test_custom_values(self):
        f = EconomyFeature(player_level=14, player_gold=12500, item_count=4, kills=8, deaths=2, assists=10)
        assert f.player_level == 14
        assert f.player_gold == 12500

    def test_json_roundtrip(self):
        f = EconomyFeature(kills=5, deaths=3, assists=7)
        data = f.model_dump()
        assert data == {"player_level": 1, "player_gold": 0, "item_count": 0, "kills": 5, "deaths": 3, "assists": 7}
        f2 = EconomyFeature.model_validate(data)
        assert f2 == f

    def test_validation_level_range(self):
        with pytest.raises(Exception):
            EconomyFeature(player_level=0)
        with pytest.raises(Exception):
            EconomyFeature(player_level=19)


class TestSkillFeature:
    def test_defaults(self):
        f = SkillFeature()
        assert f.q_ready is False
        assert f.w_ready is False
        assert f.e_ready is False
        assert f.r_ready is False
        assert f.d_ready is False
        assert f.f_ready is False

    def test_all_ready(self):
        f = SkillFeature(q_ready=True, w_ready=True, e_ready=True, r_ready=True, d_ready=True, f_ready=True)
        assert f.ult_ready is True
        assert f.flash_ready is True
        assert f.combat_ready is True

    def test_ult_ready_property(self):
        f = SkillFeature(r_ready=True)
        assert f.ult_ready is True

    def test_flash_ready_either(self):
        assert SkillFeature(d_ready=True).flash_ready is True
        assert SkillFeature(f_ready=True).flash_ready is True
        assert SkillFeature().flash_ready is False

    def test_combat_ready_requires_all_qwer(self):
        f = SkillFeature(q_ready=True, w_ready=True, e_ready=True, r_ready=False)
        assert f.combat_ready is False
        f = SkillFeature(q_ready=True, w_ready=True, e_ready=True, r_ready=True)
        assert f.combat_ready is True

    def test_json_roundtrip(self):
        f = SkillFeature(q_ready=True, r_ready=True)
        data = f.model_dump()
        f2 = SkillFeature.model_validate(data)
        assert f2 == f


class TestWaveFeature:
    def test_defaults(self):
        f = WaveFeature()
        assert f.ally_minions == 0
        assert f.enemy_minions == 0
        assert f.ally_cannons == 0
        assert f.enemy_cannons == 0

    def test_wave_strength_balanced(self):
        f = WaveFeature(ally_minions=4, enemy_minions=4)
        assert f.wave_strength == 0.0

    def test_wave_strength_ally_push(self):
        f = WaveFeature(ally_minions=8, enemy_minions=2)
        assert f.wave_strength > 0.0

    def test_wave_strength_enemy_push(self):
        f = WaveFeature(ally_minions=2, enemy_minions=8)
        assert f.wave_strength < 0.0

    def test_wave_strength_empty(self):
        f = WaveFeature()
        assert f.wave_strength == 0.0

    def test_lane_pressure_levels(self):
        assert WaveFeature().lane_pressure == "low"
        assert WaveFeature(ally_minions=6, enemy_minions=3).lane_pressure == "medium"
        assert WaveFeature(ally_minions=10, enemy_minions=1).lane_pressure == "high"

    def test_cannon_multiplier(self):
        # 1 cannon = 2 regular minions in strength
        f1 = WaveFeature(ally_cannons=1)
        f2 = WaveFeature(ally_minions=2)
        assert f1.wave_strength == f2.wave_strength


class TestObjectiveFeature:
    def test_defaults(self):
        f = ObjectiveFeature()
        assert f.dragon_alive is False
        assert f.grub_alive is False
        assert f.herald_alive is False
        assert f.baron_alive is False

    def test_all_alive(self):
        f = ObjectiveFeature(dragon_alive=True, grub_alive=True, herald_alive=True, baron_alive=True)
        assert f.dragon_alive is True
        assert f.baron_alive is True

    def test_json_roundtrip(self):
        f = ObjectiveFeature(dragon_alive=True, herald_alive=True)
        data = f.model_dump()
        f2 = ObjectiveFeature.model_validate(data)
        assert f2 == f


class TestMapFeature:
    def test_defaults(self):
        f = MapFeature()
        assert f.enemy_top == 0
        assert f.enemy_mid == 0
        assert f.enemy_bot == 0
        assert f.enemy_missing == 0

    def test_custom_values(self):
        f = MapFeature(enemy_top=1, enemy_mid=2, enemy_bot=1, enemy_missing=1)
        assert f.enemy_top == 1
        assert f.enemy_missing == 1

    def test_visible_total_property(self):
        f = MapFeature(enemy_top=1, enemy_mid=2, enemy_bot=1)
        assert f.enemy_visible_total == 4

    def test_json_roundtrip(self):
        f = MapFeature(enemy_top=1, enemy_bot=2, enemy_missing=2)
        data = f.model_dump()
        f2 = MapFeature.model_validate(data)
        assert f2 == f

    def test_validation_negative_rejected(self):
        with pytest.raises(Exception):
            MapFeature(enemy_top=-1)


class TestFeatureBundle:
    def test_defaults(self):
        from schemas.feature_bundle import FeatureBundle
        fb = FeatureBundle()
        assert fb.hero.ally_count == 0
        assert fb.economy.player_level == 1
        assert fb.skill.q_ready is False
        assert fb.wave.ally_minions == 0
        assert fb.objective.dragon_alive is False
        assert fb.map.enemy_top == 0

    def test_custom_composition(self):
        from schemas.feature_bundle import FeatureBundle
        fb = FeatureBundle(
            hero=HeroFeature(ally_count=3, enemy_count=2),
            economy=EconomyFeature(kills=5),
            skill=SkillFeature(r_ready=True),
            wave=WaveFeature(ally_minions=6, enemy_minions=3),
            objective=ObjectiveFeature(dragon_alive=True),
            map=MapFeature(enemy_top=1, enemy_mid=1, enemy_bot=1, enemy_missing=2),
        )
        assert fb.hero.ally_count == 3
        assert fb.economy.kills == 5
        assert fb.skill.ult_ready is True
        assert fb.wave.lane_pressure == "medium"
        assert fb.objective.dragon_alive is True
        assert fb.map.enemy_visible_total == 3

    def test_json_roundtrip(self):
        from schemas.feature_bundle import FeatureBundle
        fb = FeatureBundle(
            hero=HeroFeature(ally_count=2),
            economy=EconomyFeature(kills=3, deaths=1),
        )
        data = fb.model_dump()
        fb2 = FeatureBundle.model_validate(data)
        assert fb2 == fb

    def test_nested_json_structure(self):
        from schemas.feature_bundle import FeatureBundle
        fb = FeatureBundle()
        data = fb.model_dump()
        assert "hero" in data
        assert "economy" in data
        assert "skill" in data
        assert "wave" in data
        assert "objective" in data
        assert "map" in data


class TestGameStateV2:
    def test_defaults(self):
        from schemas.state import GameStateV2
        gs = GameStateV2()
        assert gs.game_time == 0.0
        assert gs.phase == "early"
        assert gs.activity == "laning"
        assert gs.context == "safe_farm"
        assert gs.combat == "even"
        assert gs.threat == "low"
        assert gs.dragon_spawn_in == -1.0
        assert gs.baron_spawn_in == -1.0
        assert gs.herald_spawn_in == -1.0

    def test_custom_values(self):
        from schemas.state import GameStateV2
        gs = GameStateV2(
            game_time=900.0,
            phase="mid",
            activity="teamfight",
            context="contest",
            combat="advantage",
            threat="high",
            dragon_spawn_in=30.0,
        )
        assert gs.game_time == 900.0
        assert gs.phase == "mid"
        assert gs.context == "contest"

    def test_json_roundtrip(self):
        from schemas.state import GameStateV2
        gs = GameStateV2(phase="late", activity="objective", context="siege")
        data = gs.model_dump()
        gs2 = GameStateV2.model_validate(data)
        assert gs2 == gs

    def test_validation_negative_time(self):
        from schemas.state import GameStateV2
        with pytest.raises(Exception):
            GameStateV2(game_time=-1.0)


class TestGoal:
    def test_defaults(self):
        from schemas.goal import Goal
        g = Goal()
        assert g.goal_type == "farm"
        assert g.confidence == 0.0

    def test_custom_values(self):
        from schemas.goal import Goal
        g = Goal(goal_type="contest_dragon", confidence=0.91)
        assert g.goal_type == "contest_dragon"
        assert g.confidence == 0.91

    def test_all_goal_types(self):
        from schemas.goal import Goal, GOAL_TYPES
        for gt in GOAL_TYPES:
            g = Goal(goal_type=gt, confidence=0.5)
            assert g.goal_type == gt
        assert len(GOAL_TYPES) == 9

    def test_json_roundtrip(self):
        from schemas.goal import Goal
        g = Goal(goal_type="push_tower", confidence=0.75)
        data = g.model_dump()
        assert data == {"goal_type": "push_tower", "confidence": 0.75}
        g2 = Goal.model_validate(data)
        assert g2 == g

    def test_validation_confidence_range(self):
        from schemas.goal import Goal
        with pytest.raises(Exception):
            Goal(confidence=1.5)
        with pytest.raises(Exception):
            Goal(confidence=-0.1)


class TestDecision:
    def test_defaults(self):
        from schemas.decision import Decision
        d = Decision()
        assert d.action == "farm"
        assert d.score == 0.0
        assert d.reason == ""

    def test_custom_values(self):
        from schemas.decision import Decision
        d = Decision(action="contest_dragon", score=95.0, reason="人数优势")
        assert d.action == "contest_dragon"
        assert d.score == 95.0
        assert d.reason == "人数优势"

    def test_json_roundtrip(self):
        from schemas.decision import Decision
        d = Decision(action="push_lane_pressure", score=65.0, reason="兵线推进")
        data = d.model_dump()
        d2 = Decision.model_validate(data)
        assert d2 == d

    def test_validation_score_range(self):
        from schemas.decision import Decision
        with pytest.raises(Exception):
            Decision(score=101.0)
        with pytest.raises(Exception):
            Decision(score=-1.0)

    def test_sorted_decisions(self):
        from schemas.decision import Decision
        decisions = [
            Decision(action="recall", score=20.0),
            Decision(action="contest_dragon", score=95.0),
            Decision(action="push_lane_pressure", score=65.0),
        ]
        sorted_d = sorted(decisions, key=lambda d: d.score, reverse=True)
        assert sorted_d[0].action == "contest_dragon"
        assert sorted_d[1].action == "push_lane_pressure"
        assert sorted_d[2].action == "recall"


class TestSchemaImports:
    def test_import_from_package(self):
        from schemas import HeroFeature, EconomyFeature, SkillFeature
        from schemas import WaveFeature, ObjectiveFeature, MapFeature
        from schemas import FeatureBundle, GameStateV2, Goal, Decision
        assert HeroFeature is not None
        assert EconomyFeature is not None
        assert SkillFeature is not None
        assert WaveFeature is not None
        assert ObjectiveFeature is not None
        assert MapFeature is not None
        assert FeatureBundle is not None
        assert GameStateV2 is not None
        assert Goal is not None
        assert Decision is not None
