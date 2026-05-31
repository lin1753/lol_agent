"""Tests for State Understanding Engine."""

import pytest

from memory.temporal_memory import TemporalMemory
from models.game_state import GameState, HeroPosition, ObjectiveStatus, Team
from reasoning.state_engine import (
    StateEngine,
    compute_game_phase,
    compute_activity,
    compute_combat_state,
    compute_lane_state,
    compute_threat_level,
    compute_objective_timers,
)


class TestPhaseEngine:
    def test_early_game(self):
        assert compute_game_phase(0) == "early_game"
        assert compute_game_phase(420) == "early_game"  # 7 min
        assert compute_game_phase(839) == "early_game"  # 13:59

    def test_mid_game(self):
        assert compute_game_phase(840) == "mid_game"  # 14:00
        assert compute_game_phase(1200) == "mid_game"  # 20 min
        assert compute_game_phase(1499) == "mid_game"  # 24:59

    def test_late_game(self):
        assert compute_game_phase(1500) == "late_game"  # 25:00
        assert compute_game_phase(3600) == "late_game"  # 60 min


class TestActivityEngine:
    def _hero(self, name, team, x=100, y=100, lane="mid"):
        return HeroPosition(name=name, team=team, x=x, y=y, lane=lane)

    def test_laning(self):
        state = GameState(
            current_time=600,
            visible_enemies=[self._hero("e1", Team.RED)],
            visible_allies=[self._hero("a1", Team.BLUE)],
        )
        mem = TemporalMemory()
        mem.update(state)
        act = compute_activity(state, mem)
        assert act == "laning"

    def test_teamfight(self):
        state = GameState(
            current_time=600,
            dragon=ObjectiveStatus(alive=False),
            baron=ObjectiveStatus(alive=False),  # No objectives to get pure teamfight
            visible_enemies=[
                self._hero("e1", Team.RED),
                self._hero("e2", Team.RED),
                self._hero("e3", Team.RED),
            ],
            visible_allies=[
                self._hero("a1", Team.BLUE),
                self._hero("a2", Team.BLUE),
                self._hero("a3", Team.BLUE),
            ],
            teamfight_probability=0.8,
        )
        mem = TemporalMemory()
        mem.update(state)
        act = compute_activity(state, mem)
        assert act == "teamfight"

    def test_objective(self):
        state = GameState(
            current_time=600,
            dragon=ObjectiveStatus(alive=True),
            teamfight_probability=0.6,
            visible_enemies=[self._hero("e1", Team.RED), self._hero("e2", Team.RED)],
            visible_allies=[self._hero("a1", Team.BLUE), self._hero("a2", Team.BLUE)],
        )
        mem = TemporalMemory()
        mem.update(state)
        act = compute_activity(state, mem)
        assert act == "objective"

    def test_roaming(self):
        state = GameState(
            current_time=600,
            visible_enemies=[],
            visible_allies=[],
        )
        mem = TemporalMemory()
        for name in ["e1", "e2", "e3"]:
            mem.update(GameState(
                current_time=500,
                visible_enemies=[HeroPosition(name=name, team=Team.RED, x=100, y=100)],
            ))
        mem.update(GameState(current_time=600))
        act = compute_activity(state, mem)
        assert act == "roaming"


class TestCombatEngine:
    def test_even(self):
        state = GameState(
            visible_enemies=[],
            visible_allies=[],
            player_hp=100,
        )
        mem = TemporalMemory()
        mem.update(state)
        cs, score = compute_combat_state(state, mem)
        assert cs == "even"

    def test_advantage(self):
        state = GameState(
            visible_enemies=[HeroPosition(name="e1", team=Team.RED, x=100, y=100)],
            visible_allies=[
                HeroPosition(name="a1", team=Team.BLUE, x=100, y=100),
                HeroPosition(name="a2", team=Team.BLUE, x=200, y=200),
            ],
            player_hp=100,
        )
        mem = TemporalMemory()
        mem.update(state)
        cs, score = compute_combat_state(state, mem)
        assert cs == "advantage"
        assert score > 0


class TestLaneEngine:
    def test_neutral(self):
        state = GameState()
        assert compute_lane_state(state) == "neutral"

    def test_pushing(self):
        state = GameState(blue_minion_count=8, red_minion_count=2)
        assert compute_lane_state(state) == "pushing"

    def test_being_pushed(self):
        state = GameState(red_minion_count=8, blue_minion_count=2)
        assert compute_lane_state(state) == "being_pushed"


class TestThreatEngine:
    def test_low(self):
        state = GameState(player_hp=100)
        mem = TemporalMemory()
        mem.update(state)
        assert compute_threat_level(state, mem) == "low"

    def test_high(self):
        state = GameState(player_hp=15, danger_lane="bot")
        mem = TemporalMemory()
        # 3 enemies missing
        for name in ["e1", "e2", "e3"]:
            mem.update(GameState(
                current_time=500,
                visible_enemies=[HeroPosition(name=name, team=Team.RED, x=100, y=100)],
            ))
        mem.update(GameState(current_time=600))
        assert compute_threat_level(state, mem) == "high"


class TestObjectiveTimers:
    def test_early_dragon(self):
        state = GameState(current_time=0, dragon_alive=True)
        timers = compute_objective_timers(state)
        assert timers["dragon_spawn_in"] == 300  # 5 min to first spawn

    def test_baron_not_spawned(self):
        state = GameState(current_time=600, baron_alive=True)
        timers = compute_objective_timers(state)
        assert timers["baron_spawn_in"] == 600  # 10 min to baron spawn

    def test_herald_window(self):
        state = GameState(current_time=900, herald_alive=True)  # 15 min
        timers = compute_objective_timers(state)
        # Herald despawns at 11 min, so at 15 min it's gone
        assert timers["herald_spawn_in"] == -1  # Not in window


class TestStateEngine:
    def test_full_understanding(self):
        engine = StateEngine()
        state = GameState(
            current_time=900,  # 15 min → mid_game
            visible_enemies=[],
            visible_allies=[],
            player_hp=100,
            dragon_alive=True,
        )
        mem = TemporalMemory()
        mem.update(state)

        result = engine.understand(state, mem)

        assert result.game_phase == "mid_game"
        assert result.activity in ("laning", "roaming")
        assert result.combat_state in ("advantage", "even", "disadvantage")
        assert result.threat_level in ("low", "medium", "high")
        assert result.dragon_spawn_in >= 0
