"""Screen capture module — supports both windowed and fullscreen games.

Two backends:
- mss: GDI-based, works for windowed/borderless mode
- dxcam: DXGI-based, works for exclusive fullscreen (DirectX) games

dxcam is preferred when available (auto-detected).
"""

from __future__ import annotations

import ctypes
from typing import Optional

import cv2
import numpy as np
from numpy.typing import NDArray

# Try dxcam for fullscreen capture
_DXCAM_AVAILABLE = False
try:
    import dxcam
    _DXCAM_AVAILABLE = True
except ImportError:
    pass


class ScreenCapture:
    """Capture the LOL game window or a fixed screen region.

    Automatically uses dxcam for fullscreen games (DXGI Desktop Duplication).
    Falls back to mss for windowed mode.

    Args:
        monitor: Monitor index (1-based) or dict with top/left/width/height.
                 Defaults to primary monitor (1).
    """

    def __init__(self, monitor: int | dict = 1) -> None:
        self._use_dxcam = False
        self._dxcam_camera = None
        self._dxcam_region = None

        # mss backend (fallback)
        import mss
        self._sct = mss.MSS()
        if isinstance(monitor, int):
            self._monitor = self._sct.monitors[monitor]
        else:
            self._monitor = monitor

        # Try dxcam
        if _DXCAM_AVAILABLE:
            try:
                self._dxcam_camera = dxcam.create(output_color="BGR")
                self._use_dxcam = True
            except Exception:
                self._dxcam_camera = None
                self._use_dxcam = False

    def get_frame(self) -> NDArray[np.uint8]:
        """Capture a single frame as a BGR numpy array (OpenCV format)."""
        if self._use_dxcam and self._dxcam_camera:
            try:
                region = self._dxcam_region
                if region:
                    frame = self._dxcam_camera.grab(region=region)
                else:
                    frame = self._dxcam_camera.grab()
                if frame is not None:
                    return frame
            except Exception:
                pass  # Fall through to mss

        # mss fallback
        raw = self._sct.grab(self._monitor)
        frame = np.array(raw)  # BGRA
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    def get_frame_raw(self) -> NDArray[np.uint8]:
        """Capture a single frame as BGRA numpy array (no conversion)."""
        raw = self._sct.grab(self._monitor)
        return np.array(raw)

    def set_window_region(
        self, x: int, y: int, width: int, height: int
    ) -> None:
        """Manually set the capture region."""
        self._monitor = {
            "top": y,
            "left": x,
            "width": width,
            "height": height,
        }
        # Also set dxcam region (left, top, right, bottom)
        if self._use_dxcam:
            self._dxcam_region = (x, y, x + width, y + height)

    def set_lol_window(self) -> bool:
        """Auto-detect and set capture region to the LOL window.

        Returns True if the LOL window was found.
        """
        try:
            hwnd = ctypes.windll.user32.FindWindowW(None, "League of Legends")
            if hwnd == 0:
                return False
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            left = rect.left
            top = rect.top
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            self.set_window_region(left, top, width, height)
            return True
        except (AttributeError, OSError):
            return False

    @property
    def width(self) -> int:
        return self._monitor["width"]

    @property
    def height(self) -> int:
        return self._monitor["height"]

    @property
    def uses_dxcam(self) -> bool:
        return self._use_dxcam and self._dxcam_camera is not None

    def close(self) -> None:
        if self._dxcam_camera:
            try:
                self._dxcam_camera.stop()
            except Exception:
                pass
        self._sct.close()

    def __enter__(self) -> ScreenCapture:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
