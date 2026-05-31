"""Overlay UI — draggable status panel with warnings and suggestions."""

from __future__ import annotations

import sys
import threading
from typing import List, Optional

from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt5.QtWidgets import QApplication, QWidget

from reasoning.rule_engine import Warning, WarningLevel


_COLORS = {
    WarningLevel.INFO: QColor(100, 180, 255),
    WarningLevel.WARN: QColor(255, 200, 50),
    WarningLevel.DANGER: QColor(255, 80, 80),
    WarningLevel.SUGGEST: QColor(120, 220, 120),
}

_ICONS = {
    "info": "●",
    "warn": "▲",
    "danger": "★",
    "suggest": "✓",
}

_PHASE_CN = {"early_game": "前期", "mid_game": "中期", "late_game": "后期"}
_CONTEXT_CN = {
    "laning": "对线", "split_push": "带线", "skirmish": "遭遇战",
    "teamfight": "团战", "dragon_fight": "小龙团", "baron_fight": "男筠团",
}
_COMBAT_CN = {"advantage": "优势", "even": "均势", "disadvantage": "劣势"}
_THREAT_CN = {"low": "低", "medium": "中", "high": "高"}
_THREAT_COLOR = {"low": QColor(100, 220, 100), "medium": QColor(255, 200, 50), "high": QColor(255, 80, 80)}


class _Signals(QObject):
    state_updated = pyqtSignal(dict)
    warnings_updated = pyqtSignal(list)


class OverlayWidget(QWidget):
    """Draggable transparent overlay showing game state and warnings."""

    def __init__(self, x: int = 1500, y: int = 50, width: int = 320) -> None:
        super().__init__()
        self._x = x
        self._y = y
        self._width = width
        self._state_info: dict = {}
        self._warnings: List[Warning] = []
        self._drag_pos = None
        self._setup_window()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setGeometry(self._x, self._y, self._width, 300)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None

    def update_state(self, state_info: dict) -> None:
        self._state_info = state_info
        self._auto_resize()
        self.update()

    def set_warnings(self, warnings: List[Warning]) -> None:
        self._warnings = list(warnings)
        self._auto_resize()
        self.update()

    def _auto_resize(self) -> None:
        n = len(self._warnings)
        has_state = bool(self._state_info)
        # Count active objective timers (show only if within 120s)
        active_obj = 0
        if has_state:
            for key in ("dragon_spawn_in", "baron_spawn_in", "herald_spawn_in"):
                v = self._state_info.get(key, -1)
                if 0 <= v <= 120:
                    active_obj += 1
        height = 10
        if has_state:
            height += 110  # time + 3 rows of state
            if active_obj > 0:
                height += 22  # objectives row
        if n > 0:
            height += 10 + min(n, 5) * 28
        height = max(80, height)
        pos = self.pos()
        self.setGeometry(pos.x(), pos.y(), self._width, height)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 8, 8)
        painter.fillPath(path, QColor(0, 0, 0, 180))

        y = 10

        # Title
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        painter.drawText(12, y + 12, "LOL Agent")
        y += 28

        # State panel
        if self._state_info:
            y = self._paint_state(painter, y)

        # Divider
        if self._warnings:
            painter.setPen(QColor(80, 80, 80))
            painter.drawLine(10, y, self.width() - 10, y)
            y += 8

        # Warnings (max 5 visible)
        painter.setFont(QFont("Microsoft YaHei", 10))
        for w in self._warnings[:5]:
            color = _COLORS.get(w.level, QColor(255, 255, 255))
            painter.setPen(color)
            icon = _ICONS.get(w.level.value, "?")
            painter.drawText(12, y + 12, f"{icon} {w.message}")
            y += 28

        painter.end()

    def _paint_state(self, p: QPainter, y: int) -> int:
        """Paint state info. Returns new y position."""
        p.setFont(QFont("Microsoft YaHei", 9))

        # Row 0: Game Time
        game_time = self._state_info.get("game_time", "")
        if game_time:
            p.setPen(QColor(255, 255, 255))
            p.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
            p.drawText(12, y + 14, f"⏱ {game_time}")
            p.setFont(QFont("Microsoft YaHei", 9))
            y += 24

        phase = _PHASE_CN.get(self._state_info.get("game_phase", ""), "?")
        ctx = _CONTEXT_CN.get(self._state_info.get("context", ""), "?")
        p.setPen(QColor(200, 200, 200))
        p.drawText(12, y + 12, f"阶段: {phase}  场景: {ctx}")
        y += 22

        combat = _COMBAT_CN.get(self._state_info.get("combat_state", ""), "?")
        threat_cn = _THREAT_CN.get(self._state_info.get("threat_level", "low"), "?")
        p.drawText(12, y + 12, f"战斗: {combat}  威胁: {threat_cn}")
        y += 22

        kda = self._state_info.get("kda", "0/0/0")
        gold = self._state_info.get("gold", 0)
        level = self._state_info.get("level", 1)
        p.drawText(12, y + 12, f"KDA: {kda}  金币: {gold}  等级: {level}")
        y += 22

        # Objectives — only show when close to spawn (within 120s)
        obj_parts = []
        for key, label in [("dragon_spawn_in", "小龙"), ("baron_spawn_in", "男筠"), ("herald_spawn_in", "先锋")]:
            v = self._state_info.get(key, -1)
            if 0 <= v <= 120:
                obj_parts.append(f"{label}: {int(v)}s")
        if obj_parts:
            p.setPen(QColor(255, 200, 50))
            p.drawText(12, y + 12, "  ".join(obj_parts))
            y += 22

        return y


class OverlayUI:
    """High-level overlay controller running in background thread."""

    def __init__(self, x: int = 1500, y: int = 50, width: int = 320) -> None:
        self._x = x
        self._y = y
        self._width = width
        self._app: QApplication | None = None
        self._widget: OverlayWidget | None = None
        self._signals: _Signals | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        import time
        for _ in range(50):
            if self._widget is not None:
                break
            time.sleep(0.1)

    def _run(self) -> None:
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._widget = OverlayWidget(self._x, self._y, self._width)
        self._signals = _Signals()
        self._signals.state_updated.connect(self._widget.update_state)
        self._signals.warnings_updated.connect(self._widget.set_warnings)
        self._widget.show()
        self._app.exec_()

    def update_state(self, state_info: dict) -> None:
        if self._signals:
            self._signals.state_updated.emit(state_info)

    def update_warnings(self, warnings: List[Warning]) -> None:
        if self._signals:
            self._signals.warnings_updated.emit(warnings)

    def stop(self) -> None:
        self._running = False
        if self._app:
            self._app.quit()

    @property
    def is_running(self) -> bool:
        return self._running
