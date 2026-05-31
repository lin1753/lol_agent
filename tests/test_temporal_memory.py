"""Tests for TemporalMemory."""

import pytest

from memory.temporal_memory import TemporalMemory
from models.game_state import GameState, HeroPosition, Team


class TestTemporalMemory:
    def _hero(self, name, team, x=100, y=100, lane="mid"):
        return HeroPosition(name=name, team=team, x=x, y=y, lane=lane)

    def test_empty(self):
        mem = TemporalMemory()
        assert mem.get_enemy_missing() == []
        assert mem.get_history() == []
        assert mem.get_jungler_missing_duration() == 0.0

    def test_update_tracks_heroes(self):
        mem = TemporalMemory()
        state = GameState(
            current_time=100.0,
            visible_enemies=[self._hero("锐雯", Team.RED, 500, 300, "top")],
            visible_allies=[self._hero("安妮", Team.BLUE, 400, 400, "mid")],
        )
        mem.update(state)

        assert mem.get_hero_memory("锐雯") is not None
        assert mem.get_hero_memory("安妮") is not None
        assert mem.get_hero_memory("不存在") is None

    def test_missing_duration(self):
        mem = TemporalMemory()

        # Frame 1: enemy visible
        state1 = GameState(
            current_time=100.0,
            visible_enemies=[self._hero("锐雯", Team.RED, 500, 300, "top")],
        )
        mem.update(state1)
        assert mem.get_enemy_missing() == []

        # Frame 2: enemy disappears
        state2 = GameState(current_time=120.0, visible_enemies=[])
        mem.update(state2)

        missing = mem.get_enemy_missing()
        assert len(missing) == 1
        assert missing[0]["name"] == "锐雯"
        assert missing[0]["missing_seconds"] == 20.0
        assert missing[0]["last_lane"] == "top"

    def test_hero_reappears(self):
        mem = TemporalMemory()

        mem.update(GameState(
            current_time=100.0,
            visible_enemies=[self._hero("锐雯", Team.RED, 500, 300, "top")],
        ))
        mem.update(GameState(current_time=120.0))  # missing
        assert len(mem.get_enemy_missing()) == 1

        # Reappears
        mem.update(GameState(
            current_time=130.0,
            visible_enemies=[self._hero("锐雯", Team.RED, 600, 400, "mid")],
        ))
        assert mem.get_enemy_missing() == []

    def test_trajectory(self):
        mem = TemporalMemory()
        for i in range(5):
            mem.update(GameState(
                current_time=float(i * 10),
                visible_enemies=[self._hero("锐雯", Team.RED, 100 + i * 10, 200)],
            ))

        traj = mem.get_hero_trajectory("锐雯")
        assert len(traj) == 5
        assert traj[0] == (0.0, 100.0, 200.0)
        assert traj[-1] == (40.0, 140.0, 200.0)

    def test_trajectory_limit(self):
        mem = TemporalMemory()
        for i in range(120):
            mem.update(GameState(
                current_time=float(i),
                visible_enemies=[self._hero("锐雯", Team.RED, 100, 200)],
            ))
        traj = mem.get_hero_trajectory("锐雯")
        assert len(traj) <= 100

    def test_history_window(self):
        mem = TemporalMemory(window_size=5)
        for i in range(10):
            mem.update(GameState(current_time=float(i)))

        history = mem.get_history()
        assert len(history) == 5
        assert history[0].current_time == 5.0
        assert history[-1].current_time == 9.0

    def test_jungler_missing(self):
        mem = TemporalMemory()
        mem.update(GameState(
            current_time=100.0,
            visible_enemies=[self._hero("赵信", Team.RED, 200, 600, "jungle")],
        ))
        mem.update(GameState(current_time=130.0))
        assert mem.get_jungler_missing_duration() == 30.0

    def test_multiple_missing_sorted(self):
        mem = TemporalMemory()
        mem.update(GameState(
            current_time=100.0,
            visible_enemies=[
                self._hero("锐雯", Team.RED, 500, 300, "top"),
                self._hero("阿狸", Team.RED, 400, 400, "mid"),
            ],
        ))
        # 锐雯 disappears at 110, 阿狸 disappears at 120
        mem.update(GameState(
            current_time=110.0,
            visible_enemies=[self._hero("阿狸", Team.RED, 400, 400, "mid")],
        ))
        mem.update(GameState(current_time=130.0))

        missing = mem.get_enemy_missing()
        assert len(missing) == 2
        # 锐雯 missing longest (30s from time 100) should be first
        assert missing[0]["name"] == "锐雯"
        assert missing[0]["missing_seconds"] == 30.0
        assert missing[1]["name"] == "阿狸"
        assert missing[1]["missing_seconds"] == 20.0

    def test_clear(self):
        mem = TemporalMemory()
        mem.update(GameState(
            current_time=100.0,
            visible_enemies=[self._hero("锐雯", Team.RED, 500, 300)],
        ))
        mem.clear()
        assert mem.get_enemy_missing() == []
        assert mem.get_history() == []
        assert mem.get_all_tracked_heroes() == {}
