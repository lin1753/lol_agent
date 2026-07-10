"""Tests for Decision Engine V2."""

import pytest


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
        goal = Goal(goal_type="farm", confidence=0.3)
        features = FeatureBundle()

        decisions = engine.evaluate(state, goal, features)
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

        decisions = engine.evaluate(state, goal, features)
        actions = [d.action for d in decisions]
        assert "contest_dragon" in actions
        cd = next(d for d in decisions if d.action == "contest_dragon")
        assert cd.score >= 70.0

    def test_contest_dragon_multi_candidates(self, engine):
        """Dragon goal produces multiple candidate actions."""
        state = GameStateV2(combat="advantage", dragon_spawn_in=35)
        goal = Goal(goal_type="contest_dragon", confidence=0.9)
        features = FeatureBundle(
            objective=ObjectiveFeature(dragon_alive=True),
            hero=HeroFeature(ally_count=3, enemy_count=2),
            wave=WaveFeature(ally_minions=5, enemy_minions=2),
        )

        decisions = engine.evaluate(state, goal, features)
        actions = {d.action for d in decisions}
        # Should have at least contest_dragon + prepare_vision or push_lane_pressure
        assert len(actions) >= 2

    def test_contest_baron_goal(self, engine):
        """Baron goal → contest_baron decision."""
        state = GameStateV2(combat="advantage", baron_spawn_in=30, phase="late")
        goal = Goal(goal_type="contest_baron", confidence=0.9)
        features = FeatureBundle(
            objective=ObjectiveFeature(baron_alive=True),
            hero=HeroFeature(ally_count=4, enemy_count=3),
        )

        decisions = engine.evaluate(state, goal, features)
        actions = [d.action for d in decisions]
        assert "contest_baron" in actions

    def test_retreat_goal(self, engine):
        """Retreat goal → retreat decision."""
        state = GameStateV2(threat="high", combat="disadvantage")
        goal = Goal(goal_type="retreat", confidence=0.8)
        features = FeatureBundle(
            hero=HeroFeature(ally_count=1, enemy_count=3),
        )

        decisions = engine.evaluate(state, goal, features)
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

        decisions = engine.evaluate(state, goal, features)
        actions = [d.action for d in decisions]
        assert "push_tower" in actions

    def test_group_goal(self, engine):
        """Group goal → group decision."""
        state = GameStateV2(combat="advantage")
        goal = Goal(goal_type="group", confidence=0.8)
        features = FeatureBundle(
            hero=HeroFeature(ally_count=4, enemy_count=2),
        )

        decisions = engine.evaluate(state, goal, features)
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

        decisions = engine.evaluate(state, goal, features)
        actions = [d.action for d in decisions]
        assert "defend_tower" in actions

    def test_split_push_goal(self, engine):
        """Split push goal → split_push decision."""
        state = GameStateV2(phase="mid")
        goal = Goal(goal_type="split_push", confidence=0.5)
        features = FeatureBundle(
            hero=HeroFeature(ally_count=3, enemy_count=1),
            map=MapFeature(enemy_missing=3),
        )

        decisions = engine.evaluate(state, goal, features)
        actions = [d.action for d in decisions]
        assert "split_push" in actions

    def test_farm_goal(self, engine):
        """Farm goal → farm decision."""
        state = GameStateV2()
        goal = Goal(goal_type="farm", confidence=0.5)
        features = FeatureBundle()

        decisions = engine.evaluate(state, goal, features)
        actions = [d.action for d in decisions]
        assert "farm" in actions

    def test_universal_missing_enemies(self, engine):
        """3+ missing enemies → play_safe warning regardless of goal."""
        state = GameStateV2()
        goal = Goal(goal_type="farm")
        features = FeatureBundle(
            map=MapFeature(enemy_missing=4),
        )

        decisions = engine.evaluate(state, goal, features)
        actions = [d.action for d in decisions]
        assert "play_safe" in actions

    def test_universal_objective_timer(self, engine):
        """Dragon about to spawn → prepare_objective."""
        state = GameStateV2(dragon_spawn_in=30)
        goal = Goal(goal_type="farm")
        features = FeatureBundle(
            objective=ObjectiveFeature(dragon_alive=True),
        )

        decisions = engine.evaluate(state, goal, features)
        actions = [d.action for d in decisions]
        assert "prepare_objective" in actions

    def test_decisions_have_reasons(self, engine):
        """All decisions have non-empty reasons."""
        state = GameStateV2(combat="advantage", dragon_spawn_in=20)
        goal = Goal(goal_type="contest_dragon", confidence=0.9)
        features = FeatureBundle(
            objective=ObjectiveFeature(dragon_alive=True),
            hero=HeroFeature(ally_count=3, enemy_count=2),
        )

        decisions = engine.evaluate(state, goal, features)
        for d in decisions:
            assert d.reason != ""
            assert 0 <= d.score <= 100.0

    def test_dragon_not_alive_skips_contest(self, engine):
        """Dragon not alive → contest_dragon decision not produced."""
        state = GameStateV2(dragon_spawn_in=20)
        goal = Goal(goal_type="contest_dragon")
        features = FeatureBundle(objective=ObjectiveFeature(dragon_alive=False))

        decisions = engine.evaluate(state, goal, features)
        actions = [d.action for d in decisions]
        assert "contest_dragon" not in actions

    def test_dedup_no_duplicate_retreat(self, engine):
        """Retreat goal + critical HP → only one retreat decision (deduped)."""
        state = GameStateV2(threat="high", combat="disadvantage")
        goal = Goal(goal_type="retreat", confidence=0.9)
        features = FeatureBundle(
            hero=HeroFeature(ally_count=1, enemy_count=3, ally_hp_total=100, enemy_hp_total=500),
        )

        decisions = engine.evaluate(state, goal, features)
        retreat_count = sum(1 for d in decisions if d.action == "retreat")
        assert retreat_count == 1
