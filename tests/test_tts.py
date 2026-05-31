"""Tests for TTS Engine."""

import time

import pytest

from reasoning.rule_engine import Warning, WarningLevel
from voice.tts_engine import TtsEngine


class TestTtsEngine:
    def test_init(self):
        engine = TtsEngine(dedup_seconds=5.0)
        assert engine.is_running is False

    def test_start_stop(self):
        engine = TtsEngine()
        engine.start()
        assert engine.is_running is True
        engine.stop()
        assert engine.is_running is False

    def test_stop_when_not_started(self):
        engine = TtsEngine()
        engine.stop()  # Should not raise

    def test_dedup_blocks_duplicate(self):
        engine = TtsEngine(dedup_seconds=10.0)
        assert engine.speak_if_new("测试消息") is True
        assert engine.speak_if_new("测试消息") is False  # deduped

    def test_dedup_allows_after_clear(self):
        engine = TtsEngine(dedup_seconds=10.0)
        engine.speak_if_new("测试")
        engine.clear_dedup()
        assert engine.speak_if_new("测试") is True

    def test_speak_warnings_filters_by_level(self):
        engine = TtsEngine(min_level=WarningLevel.WARN)
        warnings = [
            Warning(level=WarningLevel.INFO, message="info消息", rule_name="r1", category="threat"),
            Warning(level=WarningLevel.WARN, message="warn消息", rule_name="r2", category="threat"),
            Warning(level=WarningLevel.DANGER, message="danger消息", rule_name="r3", category="threat"),
        ]
        engine.speak_warnings(warnings)
        # info should be filtered, warn and danger should be queued
        # Check dedup map to verify
        assert "info消息" not in engine._dedup_map
        assert "warn消息" in engine._dedup_map
        assert "danger消息" in engine._dedup_map

    def test_speak_warnings_dedup(self):
        engine = TtsEngine(min_level=WarningLevel.INFO, dedup_seconds=10.0)
        warnings = [
            Warning(level=WarningLevel.WARN, message="重复消息", rule_name="r1", category="threat"),
        ]
        engine.speak_warnings(warnings)
        engine.speak_warnings(warnings)  # second call, same message
        # Should only be in dedup map once (second call blocked)
        assert "重复消息" in engine._dedup_map
