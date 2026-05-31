"""Tests for capture module: ScreenCapture and ROIManager."""

import json
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from capture.roi_manager import ROIManager, Region


# ---------------------------------------------------------------------------
# ROIManager tests
# ---------------------------------------------------------------------------


class TestRegion:
    def test_x2_y2(self):
        r = Region(x=10, y=20, w=100, h=200)
        assert r.x2 == 110
        assert r.y2 == 220


class TestROIManager:
    def _make_frame(self, h=1080, w=1920):
        """Create a synthetic frame with known pixel values."""
        return np.zeros((h, w, 3), dtype=np.uint8)

    def test_default_regions(self):
        mgr = ROIManager()
        assert set(mgr.region_names) == {"minimap", "topbar", "center", "hud"}

    def test_crop_minimap_shape(self):
        mgr = ROIManager()
        frame = self._make_frame()
        roi = mgr.crop(frame, "minimap")
        assert roi.shape == (300, 300, 3)

    def test_crop_topbar_shape(self):
        mgr = ROIManager()
        frame = self._make_frame()
        roi = mgr.crop(frame, "topbar")
        assert roi.shape == (120, 1300, 3)

    def test_crop_center_shape(self):
        mgr = ROIManager()
        frame = self._make_frame()
        roi = mgr.crop(frame, "center")
        assert roi.shape == (700, 1300, 3)

    def test_crop_hud_shape(self):
        mgr = ROIManager()
        frame = self._make_frame()
        roi = mgr.crop(frame, "hud")
        assert roi.shape == (230, 900, 3)

    def test_crop_all_returns_all_regions(self):
        mgr = ROIManager()
        frame = self._make_frame()
        rois = mgr.crop_all(frame)
        assert set(rois.keys()) == {"minimap", "topbar", "center", "hud"}
        for name, roi in rois.items():
            assert roi.ndim == 3

    def test_crop_preserves_pixel_values(self):
        mgr = ROIManager()
        frame = self._make_frame()
        # Set minimap region to white
        frame[780:1080, 0:300] = 255
        roi = mgr.crop(frame, "minimap")
        assert roi.max() == 255

    def test_crop_is_copy_not_view(self):
        mgr = ROIManager()
        frame = self._make_frame()
        roi = mgr.crop(frame, "minimap")
        roi[:] = 255
        # Original frame should be unchanged
        assert frame[780:1080, 0:300].max() == 0

    def test_load_config_from_json(self):
        config = {
            "resolution": [1920, 1080],
            "regions": {
                "test_region": {"x": 100, "y": 200, "w": 400, "h": 300}
            },
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config, f)
            f.flush()
            mgr = ROIManager(config_path=f.name)
        assert mgr.region_names == ["test_region"]
        frame = self._make_frame()
        roi = mgr.crop(frame, "test_region")
        assert roi.shape == (300, 400, 3)

    def test_crop_scaled_frame(self):
        """ROI should scale proportionally when frame is not 1920x1080."""
        mgr = ROIManager()
        frame = self._make_frame(h=540, w=960)
        roi = mgr.crop(frame, "minimap")
        assert roi.shape == (150, 150, 3)

    def test_invalid_region_raises(self):
        mgr = ROIManager()
        frame = self._make_frame()
        with pytest.raises(KeyError):
            mgr.crop(frame, "nonexistent")

    def test_get_region(self):
        mgr = ROIManager()
        r = mgr.get_region("minimap")
        assert isinstance(r, Region)
        assert r.x == 0 and r.y == 780 and r.w == 300 and r.h == 300


# ---------------------------------------------------------------------------
# ScreenCapture tests (limited — cannot test live capture in CI)
# ---------------------------------------------------------------------------


class TestScreenCapture:
    def test_import(self):
        from capture.screen_capture import ScreenCapture

        assert ScreenCapture is not None

    def test_context_manager(self):
        """ScreenCapture should work as a context manager without errors."""
        from capture.screen_capture import ScreenCapture

        # This will capture the full primary monitor
        with ScreenCapture(monitor=1) as sc:
            frame = sc.get_frame()
            assert frame.ndim == 3
            assert frame.shape[2] == 3  # BGR
            assert sc.width > 0
            assert sc.height > 0
