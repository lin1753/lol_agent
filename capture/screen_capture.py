"""Screen capture module using mss for real-time LOL window capture."""

from __future__ import annotations

import ctypes
from typing import Optional

import cv2
import mss
import numpy as np
from numpy.typing import NDArray


class ScreenCapture:
    """Capture the LOL game window or a fixed screen region.

    Args:
        monitor: Monitor index (1-based) or dict with top/left/width/height.
                 Defaults to primary monitor (1).
    """

    def __init__(self, monitor: int | dict = 1) -> None:
        self._sct = mss.MSS()
        if isinstance(monitor, int):
            self._monitor = self._sct.monitors[monitor]
        else:
            self._monitor = monitor

    def get_frame(self) -> NDArray[np.uint8]:
        """Capture a single frame as a BGR numpy array (OpenCV format)."""
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

    def set_lol_window(self) -> bool:
        """Auto-detect and set capture region to the LOL window.

        Returns True if the LOL window was found.
        """
        return self.find_window("League of Legends")

    def find_window(self, title: str) -> bool:
        """Find a window by title (partial match) and set capture region.

        Uses EnumWindows for fuzzy matching — LOL client titles may include
        version numbers or other suffixes.

        Returns True if the window was found.
        """
        try:
            result: list[int] = []
            title_lower = title.lower()

            @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            def _enum_callback(hwnd, _lparam):
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                        if title_lower in buf.value.lower():
                            result.append(hwnd)
                            return False  # stop enumeration
                return True

            ctypes.windll.user32.EnumWindows(_enum_callback, 0)
            if not result:
                return False

            hwnd = result[0]
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            self._monitor = {
                "top": rect.top,
                "left": rect.left,
                "width": rect.right - rect.left,
                "height": rect.bottom - rect.top,
            }
            return True
        except (AttributeError, OSError):
            return False

    @property
    def width(self) -> int:
        return self._monitor["width"]

    @property
    def height(self) -> int:
        return self._monitor["height"]

    def close(self) -> None:
        self._sct.close()

    def __enter__(self) -> ScreenCapture:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
