"""Tests for main.py integration."""

import pytest

from main import LolAgent


class TestLolAgentImport:
    def test_import(self):
        assert LolAgent is not None

    def test_init_cpu_no_model(self):
        """Verify initialization succeeds without YOLO weights."""
        agent = LolAgent(
            model_path=None,
            use_gpu=False,
            enable_overlay=False,
            enable_voice=False,
            monitor=1,
            fps_target=1.0,
        )
        assert agent._yolo is not None
        assert agent._state_parser is not None
        assert agent._memory is not None
        assert agent._rules is not None
        assert agent._overlay is None  # disabled
        assert agent._tts is None      # disabled

    def test_module_integration(self):
        """Verify modules can be chained together."""
        from capture.roi_manager import ROIManager
        from memory.temporal_memory import TemporalMemory
        from models.game_state import GameState
        from parser.state_parser import StateParser
        from perception.yolo_infer import Detection
        from reasoning.rule_engine import RuleEngine

        roi = ROIManager()
        parser = StateParser()
        memory = TemporalMemory()
        rules = RuleEngine()

        # Simulate a detection cycle
        hero_dets = [
            Detection(
                class_id=6, class_name="green_hp_hero",
                confidence=0.9, x1=400, y1=300, x2=450, y2=320,
            ),
        ]
        ocr = {"time": "10:00", "kda": "2/1/3"}

        state = parser.parse([], hero_dets, ocr)
        memory.update(state)
        warnings = rules.evaluate(state, memory)

        assert isinstance(state, GameState)
        assert state.current_time == 600.0
        assert state.kills == 2
        assert isinstance(warnings, list)
