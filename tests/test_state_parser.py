"""Tests for StateParser."""

import pytest

from models.game_state import GameState, Team
from parser.state_parser import StateParser
from perception.yolo_infer import Detection


class TestStateParser:
    @pytest.fixture
    def parser(self):
        return StateParser()

    def _det(self, cls, x1, y1, x2, y2, conf=0.9):
        return Detection(
            class_id=0, class_name=cls, confidence=conf,
            x1=x1, y1=y1, x2=x2, y2=y2,
        )

    def test_empty_input(self, parser):
        state = parser.parse([], [], {})
        assert isinstance(state, GameState)
        assert state.current_time == 0.0
        assert state.visible_enemies == []
        assert state.visible_allies == []

    def test_parse_time(self, parser):
        assert parser._parse_time("12:34") == 754
        assert parser._parse_time("0:00") == 0
        assert parser._parse_time("1:30") == 90
        assert parser._parse_time("") == 0.0
        assert parser._parse_time("abc") == 0.0

    def test_parse_kda(self, parser):
        assert parser._parse_kda("3/1/5") == (3, 1, 5)
        assert parser._parse_kda("0/0/0") == (0, 0, 0)
        assert parser._parse_kda("") == (0, 0, 0)
        assert parser._parse_kda("abc") == (0, 0, 0)

    def test_parse_int(self, parser):
        assert parser._parse_int("5500") == 5500
        assert parser._parse_int("1,234") == 1234
        assert parser._parse_int("") == 0
        assert parser._parse_int("abc") == 0

    def test_hero_detection(self, parser):
        hero_dets = [
            self._det("green_hp_hero", 400, 300, 450, 320),
            self._det("red_hp_hero", 800, 500, 850, 520),
            self._det("blue_hp_hero", 600, 400, 650, 420),
        ]
        state = parser.parse([], hero_dets, {})
        assert len(state.visible_allies) == 2  # green + blue
        assert len(state.visible_enemies) == 1  # red

    def test_minimap_detections(self, parser):
        minimap_dets = [
            self._det("enemy_hero_icon", 1700, 800, 1720, 820),
            self._det("enemy_hero_icon", 1750, 850, 1770, 870),
            self._det("ally_hero_icon", 1650, 900, 1670, 920),
        ]
        state = parser.parse(minimap_dets, [], {})
        assert len(state.minimap_enemy_positions) == 2
        assert len(state.minimap_ally_positions) == 1

    def test_ocr_parsing(self, parser):
        ocr = {"time": "15:30", "kda": "5/2/8", "gold": "8500", "level": "13"}
        state = parser.parse([], [], ocr)
        assert state.current_time == 930.0
        assert state.kills == 5
        assert state.deaths == 2
        assert state.assists == 8
        assert state.current_gold == 8500
        assert state.player_level == 13

    def test_full_parse(self, parser):
        minimap = [
            self._det("enemy_hero_icon", 1700, 800, 1720, 820),
            self._det("enemy_hero_icon", 1600, 850, 1620, 870),
            self._det("enemy_hero_icon", 1750, 900, 1770, 920),
            self._det("ally_hero_icon", 1650, 950, 1670, 970),
            self._det("blue_tower", 1650, 800, 1670, 820),
            self._det("red_tower", 1750, 950, 1770, 970),
        ]
        heroes = [
            self._det("green_hp_hero", 400, 200, 450, 220),
            self._det("red_hp_hero", 800, 400, 850, 420),
            self._det("red_hp_hero", 900, 500, 950, 520),
        ]
        ocr = {"time": "20:00", "kda": "10/3/15", "gold": "12000", "level": "18"}

        state = parser.parse(minimap, heroes, ocr)
        assert state.current_time == 1200.0
        assert state.kills == 10
        assert len(state.visible_enemies) == 2
        assert len(state.visible_allies) == 1
        assert len(state.minimap_enemy_positions) == 3
        assert state.blue_towers_alive == 1
        assert state.red_towers_alive == 1
        assert state.player_level == 18

    def test_lane_estimation(self, parser):
        hero_top = self._det("green_hp_hero", 500, 100, 550, 120)
        hero_bot = self._det("red_hp_hero", 500, 900, 550, 920)
        state = parser.parse([], [hero_top, hero_bot], {})
        assert state.visible_allies[0].lane == "top"
        assert state.visible_enemies[0].lane == "bot"
