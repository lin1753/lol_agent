"""Tests for GameState pydantic model."""

import json

import pytest

from models.game_state import GameState, HeroPosition, ObjectiveStatus, Team


class TestHeroPosition:
    def test_create(self):
        h = HeroPosition(name="安妮", team=Team.RED, x=100.0, y=200.0)
        assert h.name == "安妮"
        assert h.team == Team.RED
        assert h.lane is None

    def test_with_lane(self):
        h = HeroPosition(name="赵信", team=Team.BLUE, x=50, y=50, lane="jungle")
        assert h.lane == "jungle"


class TestObjectiveStatus:
    def test_default_alive(self):
        obj = ObjectiveStatus()
        assert obj.alive is True
        assert obj.last_killed_time is None

    def test_killed(self):
        obj = ObjectiveStatus(alive=False, last_killed_time=600.0, respawn_time=810.0)
        assert obj.alive is False


class TestGameState:
    def test_default_state(self):
        gs = GameState()
        assert gs.current_time == 0.0
        assert gs.visible_enemies == []
        assert gs.visible_allies == []
        assert gs.enemy_missing == []
        assert gs.dragon.alive is True
        assert gs.player_hp == 100.0
        assert gs.teamfight_probability == 0.0

    def test_with_data(self):
        gs = GameState(
            current_time=900.0,
            visible_enemies=[
                HeroPosition(name="锐雯", team=Team.RED, x=500, y=300, lane="top"),
            ],
            visible_allies=[
                HeroPosition(name="安妮", team=Team.BLUE, x=400, y=400, lane="mid"),
                HeroPosition(name="赵信", team=Team.BLUE, x=200, y=600, lane="jungle"),
            ],
            enemy_missing=["阿狸", "薇恩", "锤石"],
            player_hp=75.5,
            kills=3,
            deaths=1,
            assists=5,
            danger_lane="bot",
            teamfight_probability=0.6,
        )
        assert gs.current_time == 900.0
        assert gs.enemy_count_visible == 1
        assert gs.ally_count_visible == 2
        assert gs.missing_enemy_count == 3
        assert gs.player_hp == 75.5
        assert gs.kills == 3
        assert gs.danger_lane == "bot"

    def test_serialization(self):
        gs = GameState(current_time=120.0, kills=2, deaths=0, assists=1)
        data = gs.model_dump()
        assert data["current_time"] == 120.0
        assert data["kills"] == 2

        # Round-trip through JSON
        json_str = gs.model_dump_json()
        gs2 = GameState.model_validate_json(json_str)
        assert gs2.current_time == 120.0
        assert gs2.kills == 2

    def test_minimap_positions(self):
        gs = GameState(
            minimap_enemy_positions={"锐雯": (100.0, 200.0)},
            minimap_ally_positions={"安妮": (300.0, 400.0)},
        )
        assert gs.get_hero_on_minimap("锐雯") == (100.0, 200.0)
        assert gs.get_hero_on_minimap("安妮") == (300.0, 400.0)
        assert gs.get_hero_on_minimap("不存在") is None

    def test_validation_hp_range(self):
        gs = GameState(player_hp=50.0)
        assert gs.player_hp == 50.0

        with pytest.raises(Exception):
            GameState(player_hp=150.0)

    def test_validation_probability_range(self):
        gs = GameState(teamfight_probability=0.8)
        assert gs.teamfight_probability == 0.8

        with pytest.raises(Exception):
            GameState(teamfight_probability=1.5)

    def test_objectives(self):
        gs = GameState(
            dragon=ObjectiveStatus(alive=False, last_killed_time=300.0),
            baron=ObjectiveStatus(alive=True),
        )
        assert gs.dragon.alive is False
        assert gs.baron.alive is True
