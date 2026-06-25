"""Tests for TTS Engine."""

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
