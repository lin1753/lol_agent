"""Tests for Goal Engine (P2-T2)."""

import pytest

from memory.temporal_memory import TemporalMemory
from reasoning.goal_engine import GoalEngine
from schemas.feature_bundle import FeatureBundle
from schemas.hero import HeroFeature
from schemas.map import MapFeature
from schemas.objective import ObjectiveFeature
from schemas.state import GameStateV2
from schemas.wave import WaveFeature
from schemas.goal import GOAL_TYPES


class TestGoalEngine:
    @pytest.fixture
    def engine(self):
        return GoalEngine()

    def test_default_reset(self, engine):
        """No strong conditions → reset."""
        features = FeatureBundle()
        state = GameStateV2()
        mem = TemporalMemory()
        goal = engine.determine(state, features, mem)
        assert goal.goal_type == "reset"
        assert 0 < goal.confidence <= 1.0

    def test_contest_dragon(self, engine):
        """Dragon alive + spawning soon + combat advantage → contest_dragon."""
        features = FeatureBundle(
            objective=ObjectiveFeature(dragon_alive=True),
            hero=HeroFeature(ally_count=3, enemy_count=2),
        )
        state = GameStateV2(
            dragon_spawn_in=30, combat="advantage",
            phase="mid",
        )
        mem = TemporalMemory()
        goal = engine.determine(state, features, mem)
        assert goal.goal_type == "contest_dragon"
        assert goal.confidence > 0.5

    def test_contest_baron_late(self, engine):
        """Baron in late game → higher confidence."""
        features = FeatureBundle(
            objective=ObjectiveFeature(baron_alive=True),
            hero=HeroFeature(ally_count=4, enemy_count=3),
        )
        state = GameStateV2(
            baron_spawn_in=60, combat="advantage",
            phase="late",
        )
        mem = TemporalMemory()
        goal = engine.determine(state, features, mem)
        assert goal.goal_type == "contest_baron"
        assert goal.confidence > 0.6

    def test_contest_herald(self, engine):
        """Herald alive + spawning soon → contest_herald."""
        features = FeatureBundle(
            objective=ObjectiveFeature(herald_alive=True),
            hero=HeroFeature(ally_count=2, enemy_count=2),
        )
        state = GameStateV2(herald_spawn_in=30)
        mem = TemporalMemory()
        goal = engine.determine(state, features, mem)
        assert goal.goal_type == "contest_herald"

    def test_retreat_high_threat(self, engine):
        """High threat → retreat."""
        features = FeatureBundle()
        state = GameStateV2(threat="high")
        mem = TemporalMemory()
        goal = engine.determine(state, features, mem)
        assert goal.goal_type == "retreat"
        assert goal.confidence == 0.8

    def test_retreat_combat_disadvantage(self, engine):
        """Combat disadvantage → retreat."""
        features = FeatureBundle()
        state = GameStateV2(combat="disadvantage")
        mem = TemporalMemory()
        goal = engine.determine(state, features, mem)
        assert goal.goal_type == "retreat"

    def test_group_advantage(self, engine):
        """Combat advantage + 3+ allies → group."""
        features = FeatureBundle(
            hero=HeroFeature(ally_count=4, enemy_count=2),
        )
        state = GameStateV2(combat="advantage")
        mem = TemporalMemory()
        goal = engine.determine(state, features, mem)
        assert goal.goal_type == "group"
        assert goal.confidence > 0.7

    def test_push_tower(self, engine):
        """Wave advantage + enemies missing + not early → push_tower."""
        features = FeatureBundle(
            wave=WaveFeature(ally_minions=8, enemy_minions=3),
            map=MapFeature(enemy_missing=3),
        )
        state = GameStateV2(phase="mid")
        mem = TemporalMemory()
        goal = engine.determine(state, features, mem)
        assert goal.goal_type == "push_tower"

    def test_defend_tower(self, engine):
        """Enemy minions pushing + enemies present → defend_tower."""
        features = FeatureBundle(
            wave=WaveFeature(enemy_minions=6),
            hero=HeroFeature(enemy_count=3, ally_count=1),
        )
        state = GameStateV2()
        mem = TemporalMemory()
        goal = engine.determine(state, features, mem)
        assert goal.goal_type == "defend_tower"

    def test_split_push(self, engine):
        """Mid/late game + ally advantage + enemies missing → split_push."""
        features = FeatureBundle(
            hero=HeroFeature(ally_count=4, enemy_count=2),
            map=MapFeature(enemy_missing=3),
        )
        state = GameStateV2(phase="late")
        mem = TemporalMemory()
        goal = engine.determine(state, features, mem)
        # Could be group or split_push depending on scores
        assert goal.goal_type in ("split_push", "group")

    def test_confidence_range(self, engine):
        """All goals have confidence in [0, 1]."""
        features = FeatureBundle()
        for phase in ("early", "mid", "late"):
            for combat in ("advantage", "even", "disadvantage"):
                for threat in ("low", "medium", "high"):
                    state = GameStateV2(phase=phase, combat=combat, threat=threat)
                    mem = TemporalMemory()
                    goal = engine.determine(state, features, mem)
                    assert 0 <= goal.confidence <= 1.0
                    assert goal.goal_type in GOAL_TYPES

    def test_contest_not_triggered_when_no_objective(self, engine):
        """No objectives alive → no contest goals."""
        features = FeatureBundle(
            objective=ObjectiveFeature(),
        )
        state = GameStateV2(dragon_spawn_in=30, baron_spawn_in=60)
        mem = TemporalMemory()
        goal = engine.determine(state, features, mem)
        assert goal.goal_type not in ("contest_dragon", "contest_baron", "contest_herald")
