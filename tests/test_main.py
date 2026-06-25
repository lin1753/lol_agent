"""Tests for main.py integration."""

from config import AgentConfig
from main import LolAgent


class TestLolAgentImport:
    def test_import(self):
        assert LolAgent is not None

    def test_init_cpu_no_model(self):
        """Verify initialization succeeds without YOLO weights."""
        cfg = AgentConfig()
        cfg.yolo_model = None
        agent = LolAgent(
            config=cfg,
            enable_overlay=False,
            enable_voice=False,
            monitor=1,
        )
        assert agent._yolo is not None
        assert agent._feature_engine is not None
        assert agent._context_engine is not None
        assert agent._goal_engine is not None
        assert agent._objective_memory is not None
        assert agent._overlay is None
        assert agent._tts is None
