"""Tests for AgentConfig."""

import os
from types import SimpleNamespace

from config import AgentConfig


class TestAgentConfig:
    def test_defaults(self):
        cfg = AgentConfig()
        assert cfg.fps_target == 5.0
        assert cfg.ocr_lang == "ch"
        assert cfg.ocr_interval == 60
        assert cfg.status_interval == 30
        assert cfg.baron_first_spawn == 1500
        assert cfg.herald_despawn == 1170
        assert cfg.overlay_x == 1500

    def test_from_args_override(self):
        args = SimpleNamespace(fps=10.0, model="weights.pt", llm_model="/path/to/model")
        cfg = AgentConfig.from_args(args)
        assert cfg.fps_target == 10.0
        assert cfg.yolo_model == "weights.pt"
        assert cfg.llm_model == "/path/to/model"

    def test_from_args_env_fallback(self, monkeypatch):
        monkeypatch.setenv("LOL_LLM_MODEL_PATH", "/env/model")
        args = SimpleNamespace(fps=None, model=None, llm_model=None)
        cfg = AgentConfig.from_args(args)
        assert cfg.llm_model == "/env/model"

    def test_from_args_no_env(self, monkeypatch):
        monkeypatch.delenv("LOL_LLM_MODEL_PATH", raising=False)
        args = SimpleNamespace(fps=None, model=None, llm_model=None)
        cfg = AgentConfig.from_args(args)
        assert cfg.llm_model is None
