"""Tests for LLM Engine (P3-T1) — mock LLM, no actual model loading."""

import json

import pytest

from reasoning.llm_engine import LlmEngine
from schemas.decision import Decision
from schemas.goal import Goal
from schemas.state import GameStateV2


class TestLlmEngine:
    @pytest.fixture
    def engine(self):
        """Create engine without loading model."""
        return LlmEngine(model_path="test-model", quantize=False)

    def test_not_ready_by_default(self, engine):
        assert engine._ready is False
        assert engine._model is None

    def test_advise_returns_none_when_not_ready(self, engine):
        state = GameStateV2()
        goal = Goal()
        result = engine.advise(state, goal, [])
        assert result is None

    def test_build_prompt_structure(self, engine):
        state = GameStateV2(
            phase="mid", activity="teamfight", context="contest",
            combat="advantage", threat="medium", game_time=900,
        )
        goal = Goal(goal_type="contest_dragon", confidence=0.91)
        decisions = [
            Decision(action="contest_dragon", score=95.0, reason="人数优势"),
            Decision(action="push_lane_pressure", score=65.0, reason="兵线推进"),
        ]
        prompt = LlmEngine._build_prompt(state, goal, decisions)

        # Should be valid JSON embedded in the prompt
        assert "contest_dragon" in prompt
        assert "0.91" in prompt
        assert "人数优势" in prompt
        assert "15:00" in prompt  # 900s = 15:00

    def test_build_prompt_top_3_decisions(self, engine):
        state = GameStateV2()
        goal = Goal()
        decisions = [
            Decision(action="contest_dragon", score=90, reason="r1"),
            Decision(action="push_tower", score=80, reason="r2"),
            Decision(action="farm", score=70, reason="r3"),
        ]
        prompt = LlmEngine._build_prompt(state, goal, decisions)
        assert "contest_dragon" in prompt  # Top 1 shown
        assert "r1" in prompt
        assert "push_tower" not in prompt  # Only top 1 in new format

    def test_should_advise_on_goal_change(self, engine):
        state = GameStateV2()
        goal1 = Goal(goal_type="farm")
        goal2 = Goal(goal_type="contest_dragon")

        # First call with goal1
        assert engine.should_advise(state, goal1) is True
        engine._last_goal = goal1.goal_type

        # Same goal → depends on interval
        engine._last_advise_time = __import__("time").time()  # just now
        assert engine.should_advise(state, goal1) is False

        # Different goal → should advise
        assert engine.should_advise(state, goal2) is True

    def test_should_advise_on_interval(self, engine):
        state = GameStateV2()
        goal = Goal(goal_type="farm")
        engine._last_goal = "farm"
        engine._last_advise_time = 0  # long ago

        assert engine.should_advise(state, goal) is True

    def test_stop_resets_state(self, engine):
        engine._ready = True
        engine._model = "fake"
        engine._tokenizer = "fake"
        engine.stop()
        assert engine._ready is False
        assert engine._model is None
        assert engine._tokenizer is None

    def test_prompt_contains_json(self, engine):
        state = GameStateV2(phase="late", combat="disadvantage")
        goal = Goal(goal_type="retreat", confidence=0.8)
        decisions = [Decision(action="retreat", score=85, reason="劣势后撤")]
        prompt = LlmEngine._build_prompt(state, goal, decisions)

        # New format: state JSON at top level, goal/action in plain text
        json_start = prompt.find("{")
        json_end = prompt.rfind("}") + 1
        json_str = prompt[json_start:json_end]
        data = json.loads(json_str)
        assert data["phase"] == "late"
        assert "retreat" in prompt  # goal and action in prompt text
