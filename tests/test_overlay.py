"""Tests for Overlay UI (status panel)."""

import pytest

from reasoning.rule_engine import Warning, WarningLevel
from overlay.overlay_ui import OverlayUI, OverlayWidget, _COLORS, _ICONS


class TestWarningColors:
    def test_all_levels_have_colors(self):
        for level in WarningLevel:
            assert level in _COLORS

    def test_all_levels_have_icons(self):
        for level in WarningLevel:
            assert level.value in _ICONS


class TestOverlayImports:
    def test_import(self):
        assert OverlayWidget is not None
        assert OverlayUI is not None

    def test_warning_creation(self):
        w = Warning(
            level=WarningLevel.DANGER,
            message="test warning",
            rule_name="test",
            category="threat",
            timestamp=100.0,
        )
        assert w.level == WarningLevel.DANGER
        assert w.message == "test warning"

    def test_suggestion_flag(self):
        w = Warning(
            level=WarningLevel.SUGGEST,
            message="test suggestion",
            rule_name="test_sug",
            category="combat",
            is_suggestion=True,
        )
        assert w.is_suggestion is True

    def test_warning_hash(self):
        w1 = Warning(level=WarningLevel.INFO, message="a", rule_name="r1", category="threat")
        w2 = Warning(level=WarningLevel.INFO, message="a", rule_name="r1", category="threat")
        assert hash(w1) == hash(w2)


class TestOverlayUI:
    def test_init(self):
        overlay = OverlayUI(x=100, y=100, width=300)
        assert overlay.is_running is False

    def test_stop_when_not_started(self):
        overlay = OverlayUI()
        overlay.stop()  # Should not raise
