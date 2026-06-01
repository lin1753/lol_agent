"""Tests for Context Engine (P2-T1)."""

import pytest

from memory.temporal_memory import TemporalMemory
from reasoning.context_engine import ContextEngine, CONTEXT_TYPES
from schemas.economy import EconomyFeature
from schemas.feature_bundle import FeatureBundle
from schemas.hero import HeroFeature
from schemas.map import MapFeature
from schemas.objective import ObjectiveFeature
from schemas.state import GameStateV2
from schemas.wave import WaveFeature


class TestContextEngine:
    @pytest.fixture
    def engine(self):
        return ContextEngine()

    def test_safe_farm_default(self, engine):
        """Low activity → safe_farm."""
        features = FeatureBundle()
        state = GameStateV2()
        mem = TemporalMemory()
        assert engine.compute(features, state, mem) == "safe_farm"

    def test_retreat_high_threat_disadvantage(self, engine):
        """High threat + combat disadvantage → retreat."""
        features = FeatureBundle()
        state = GameStateV2(threat="high", combat="disadvantage")
        mem = TemporalMemory()
        assert engine.compute(features, state, mem) == "retreat"

    def test_retreat_takes_priority(self, engine):
        """Retreat overrides other conditions when threat=high + disadvantage."""
        features = FeatureBundle(
            wave=WaveFeature(ally_minions=8, enemy_minions=2),
            hero=HeroFeature(ally_count=4, enemy_count=1),
        )
        state = GameStateV2(threat="high", combat="disadvantage")
        mem = TemporalMemory()
        assert engine.compute(features, state, mem) == "retreat"

    def test_collapse_enemy_pushing(self, engine):
        """3+ enemies + many minions + few allies → collapse."""
        features = FeatureBundle(
            wave=WaveFeature(enemy_minions=7),
            hero=HeroFeature(enemy_count=3, ally_count=1),
        )
        state = GameStateV2()
        mem = TemporalMemory()
        assert engine.compute(features, state, mem) == "collapse"

    def test_contest_dragon_soon(self, engine):
        """Dragon spawning soon + both sides present → contest."""
        features = FeatureBundle(
            hero=HeroFeature(ally_count=3, enemy_count=2),
        )
        state = GameStateV2(dragon_spawn_in=30)
        mem = TemporalMemory()
        assert engine.compute(features, state, mem) == "contest"

    def test_contest_baron_soon(self, engine):
        """Baron spawning soon + both sides → contest."""
        features = FeatureBundle(
            hero=HeroFeature(ally_count=2, enemy_count=3),
        )
        state = GameStateV2(baron_spawn_in=60)
        mem = TemporalMemory()
        assert engine.compute(features, state, mem) == "contest"

    def test_siege_ally_pushing(self, engine):
        """Many ally minions + ally advantage + few enemies → siege."""
        features = FeatureBundle(
            wave=WaveFeature(ally_minions=6),
            hero=HeroFeature(ally_count=4, enemy_count=1),
        )
        state = GameStateV2()
        mem = TemporalMemory()
        assert engine.compute(features, state, mem) == "siege"

    def test_defense_enemy_pushing(self, engine):
        """Enemy minions + enemies present + few allies → defense."""
        features = FeatureBundle(
            wave=WaveFeature(enemy_minions=5),
            hero=HeroFeature(enemy_count=3, ally_count=1),
        )
        state = GameStateV2()
        mem = TemporalMemory()
        assert engine.compute(features, state, mem) == "defense"

    def test_pressure_wave_advantage_missing(self, engine):
        """Wave advantage + enemies missing + not high threat → pressure."""
        features = FeatureBundle(
            wave=WaveFeature(ally_minions=8, enemy_minions=3),
            map=MapFeature(enemy_missing=3),
        )
        state = GameStateV2(threat="low")
        mem = TemporalMemory()
        assert engine.compute(features, state, mem) == "pressure"

    def test_all_context_types_exist(self):
        """All 7 context types are defined."""
        assert len(CONTEXT_TYPES) == 7
        expected = {"safe_farm", "pressure", "siege", "defense", "contest", "collapse", "retreat"}
        assert set(CONTEXT_TYPES) == expected
