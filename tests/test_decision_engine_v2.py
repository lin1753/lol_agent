"""Tests for Decision Engine V2 (P2-T3)."""

import pytest

from memory.temporal_memory import TemporalMemory
from reasoning.decision_engine_v2 import DecisionEngineV2
from schemas.feature_bundle import FeatureBundle
from schemas.goal import Goal
from schemas.hero import HeroFeature
from schemas.map import MapFeature
from schemas.objective import ObjectiveFeature
from schemas.state import GameStateV2
from schemas.wave import WaveFeature


class TestDecisionEngineV2:
    @pytest.fixture
    def engine(self):
        return DecisionEngineV2()

    def test_returns_sorted_decisions(self, engine):
        """Decisions are sorted by score descending."""
        state = GameStateV2()
        goal = Goal(goal_type="reset", confidence=0.3)
        features = FeatureBundle()
        mem = TemporalMemory()
        decisions = engine.evaluate(state, goal, features, mem)
        assert len(decisions) >= 1
        for i in range(len(decisions) - 1):
            assert decisions[i].score >= decisions[i + 1].score

    def test_contest_dragon_goal(self, engine):
        """Dragon goal → contest_dragon decision with high score."""
        state = GameStateV2(combat="advantage", dragon_spawn_in=20)
        goal = Goal(goal_type="contest_dragon", confidence=0.9)
        features = FeatureBundle(
            objective=ObjectiveFeature(dragon_alive=True),
            hero=HeroFeature(ally_count=3, enemy_count=2),
        )
        mem = TemporalMemory()
        decisions = engine.evaluate(state, goal, features, mem)
        actions = [d.action for d in decisions]
        assert "contest_dragon" in actions
        cd = next(d for d in decisions if d.action == "contest_dragon")
        assert cd.score >= 80.0  # advantage + numbers + close spawn

    def test_contest_baron_goal(self, engine):
        """Baron goal → contest_baron decision."""
        state = GameStateV2(combat="advantage", baron_spawn_in=30, phase="late")
        goal = Goal(goal_type="contest_baron", confidence=0.9)
        features = FeatureBundle(
            objective=ObjectiveFeature(baron_alive=True),
            hero=HeroFeature(ally_count=4, enemy_count=3),
        )
        mem = TemporalMemory()
        decisions = engine.evaluate(state, goal, features, mem)
        actions = [d.action for d in decisions]
        assert "contest_baron" in actions

    def test_retreat_goal(self, engine):
        """Retreat goal → retreat decision."""
        state = GameStateV2(threat="high", combat="disadvantage")
        goal = Goal(goal_type="retreat", confidence=0.8)
        features = FeatureBundle(
            hero=HeroFeature(ally_count=1, enemy_count=3),
        )
        mem = TemporalMemory()
        decisions = engine.evaluate(state, goal, features, mem)
        actions = [d.action for d in decisions]
        assert "retreat" in actions
        rd = next(d for d in decisions if d.action == "retreat")
        assert rd.score >= 80.0

    def test_push_tower_goal(self, engine):
        """Push tower goal → push_tower decision."""
        state = GameStateV2(combat="advantage")
        goal = Goal(goal_type="push_tower", confidence=0.7)
        features = FeatureBundle(
            wave=WaveFeature(ally_minions=8, enemy_minions=2),
            map=MapFeature(enemy_missing=3),
        )
        mem = TemporalMemory()
        decisions = engine.evaluate(state, goal, features, mem)
        actions = [d.action for d in decisions]
        assert "push_tower" in actions

    def test_group_goal(self, engine):
        """Group goal → group decision."""
        state = GameStateV2(combat="advantage")
        goal = Goal(goal_type="group", confidence=0.8)
        features = FeatureBundle(
            hero=HeroFeature(ally_count=4, enemy_count=2),
        )
        mem = TemporalMemory()
        decisions = engine.evaluate(state, goal, features, mem)
        actions = [d.action for d in decisions]
        assert "group" in actions

    def test_defend_tower_goal(self, engine):
        """Defend tower goal → defend_tower decision."""
        state = GameStateV2()
        goal = Goal(goal_type="defend_tower", confidence=0.7)
        features = FeatureBundle(
            wave=WaveFeature(enemy_minions=6),
            hero=HeroFeature(enemy_count=3),
        )
        mem = TemporalMemory()
        decisions = engine.evaluate(state, goal, features, mem)
        actions = [d.action for d in decisions]
        assert "defend_tower" in actions

    def test_split_push_goal(self, engine):
        """Split push goal → split_push decision."""
        state = GameStateV2()
        goal = Goal(goal_type="split_push", confidence=0.5)
        features = FeatureBundle(
            map=MapFeature(enemy_missing=3),
        )
        mem = TemporalMemory()
        decisions = engine.evaluate(state, goal, features, mem)
        actions = [d.action for d in decisions]
        assert "split_push" in actions

    def test_reset_goal(self, engine):
        """Reset goal → reset decision."""
        state = GameStateV2()
        goal = Goal(goal_type="reset", confidence=0.3)
        features = FeatureBundle()
        mem = TemporalMemory()
        decisions = engine.evaluate(state, goal, features, mem)
        actions = [d.action for d in decisions]
        assert "reset" in actions

    def test_universal_missing_enemies(self, engine):
        """3+ missing enemies → play_safe warning regardless of goal."""
        state = GameStateV2()
        goal = Goal(goal_type="reset")
        features = FeatureBundle(
            map=MapFeature(enemy_missing=4),
        )
        mem = TemporalMemory()
        decisions = engine.evaluate(state, goal, features, mem)
        actions = [d.action for d in decisions]
        assert "play_safe" in actions

    def test_universal_objective_timer(self, engine):
        """Dragon about to spawn → prepare_dragon warning."""
        state = GameStateV2(dragon_spawn_in=15)
        goal = Goal(goal_type="reset")
        features = FeatureBundle(
            objective=ObjectiveFeature(dragon_alive=True),
        )
        mem = TemporalMemory()
        decisions = engine.evaluate(state, goal, features, mem)
        actions = [d.action for d in decisions]
        assert "prepare_dragon" in actions

    def test_decisions_have_reasons(self, engine):
        """All decisions have non-empty reasons."""
        state = GameStateV2(combat="advantage", dragon_spawn_in=20)
        goal = Goal(goal_type="contest_dragon", confidence=0.9)
        features = FeatureBundle(
            objective=ObjectiveFeature(dragon_alive=True),
            hero=HeroFeature(ally_count=3, enemy_count=2),
        )
        mem = TemporalMemory()
        decisions = engine.evaluate(state, goal, features, mem)
        for d in decisions:
            assert d.reason != ""
            assert 0 <= d.score <= 100.0

    def test_dragon_not_alive_skips_contest(self, engine):
        """Dragon not alive → contest_dragon decision not produced."""
        state = GameStateV2(dragon_spawn_in=20)
        goal = Goal(goal_type="contest_dragon")
        features = FeatureBundle(objective=ObjectiveFeature(dragon_alive=False))
        mem = TemporalMemory()
        decisions = engine.evaluate(state, goal, features, mem)
        actions = [d.action for d in decisions]
        assert "contest_dragon" not in actions
