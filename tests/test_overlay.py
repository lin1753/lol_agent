"""Tests for Overlay UI (status panel)."""

from overlay.overlay_ui import OverlayUI, OverlayWidget, _WARNING_COLORS, _ICONS


class TestWarningColors:
    def test_all_levels_have_colors(self):
        for level in ("info", "warn", "danger", "suggest"):
            assert level in _WARNING_COLORS

    def test_all_levels_have_icons(self):
        for level in ("info", "warn", "danger", "suggest"):
            assert level in _ICONS


class TestOverlayImports:
    def test_import(self):
        assert OverlayWidget is not None
        assert OverlayUI is not None


class TestOverlayUI:
    def test_init(self):
        overlay = OverlayUI(x=100, y=100, width=300)
        assert overlay.is_running is False

    def test_stop_when_not_started(self):
        overlay = OverlayUI()
        overlay.stop()  # Should not raise
