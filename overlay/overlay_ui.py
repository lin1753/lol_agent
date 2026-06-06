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
_ACTIVITY_CN = {
    "laning": "对线", "roaming": "游走", "skirmish": "遭遇战",
    "teamfight": "团战", "objective": "目标争夺",
}
_COMBAT_CN = {"advantage": "优势", "even": "均势", "disadvantage": "劣势"}
_THREAT_CN = {"low": "低", "medium": "中", "high": "高"}
_THREAT_COLOR = {"low": QColor(100, 220, 100), "medium": QColor(255, 200, 50), "high": QColor(255, 80, 80)}
_CONTEXT_CN = {
    "safe_farm": "安全发育", "pressure": "施压", "siege": "围攻",
    "defense": "防守", "contest": "争夺", "collapse": "崩盘", "retreat": "撤退",
}
_GOAL_CN = {
    "contest_dragon": "争夺小龙", "contest_baron": "争夺男爵", "contest_herald": "争夺先锋",
    "push_tower": "推塔", "defend_tower": "防守", "split_push": "分推",
    "group": "集合团战", "retreat": "后撤", "reset": "回城补给",
}
_GOAL_COLOR = QColor(100, 200, 255)
_DECISION_COLOR = QColor(180, 220, 180)


class _Signals(QObject):
    state_updated = pyqtSignal(dict)
    warnings_updated = pyqtSignal(list)
    decisions_updated = pyqtSignal(list)


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
        activity = _ACTIVITY_CN.get(self._state_info.get("activity", ""), "?")
        p.setPen(QColor(200, 200, 200))
        p.drawText(12, y + 12, f"阶段: {phase}  活动: {activity}")
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


class OverlayWidgetV2(OverlayWidget):
    """V2 overlay with Goal, Context, Decision display."""

    def __init__(self, x: int = 1500, y: int = 50, width: int = 320) -> None:
        super().__init__(x, y, width)
        self._decisions: list = []

    def set_decisions(self, decisions: list) -> None:
        self._decisions = list(decisions)
        self._auto_resize()
        self.update()

    def _auto_resize(self) -> int:
        n_warn = len(self._warnings)
        n_dec = min(len(self._decisions), 3)
        has_state = bool(self._state_info)

        active_obj = 0
        if has_state:
            for key in ("dragon_spawn_in", "baron_spawn_in", "herald_spawn_in"):
                v = self._state_info.get(key, -1)
                if 0 <= v <= 120:
                    active_obj += 1

        # Title(28) + time(24) + state-row(22) + combat-row(22) + context-row(22)
        height = 10 + 28 + 24 + 22 + 22
        if has_state:
            # Context row
            if self._state_info.get("context"):
                height += 22
            # Goal row
            if self._state_info.get("goal_type"):
                height += 26
            # Decisions
            if n_dec > 0:
                height += n_dec * 22 + 6
            # KDA row
            height += 22
            # Objectives
            if active_obj > 0:
                height += 22
        if n_warn > 0:
            height += 10 + min(n_warn, 5) * 28
        # Advice
        if self._state_info.get("advice"):
            height += 28
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
        painter.drawText(12, y + 12, "LOL Agent V2")
        y += 28

        if self._state_info:
            y = self._paint_v2_state(painter, y)

        # Warnings (max 5)
        if self._warnings:
            painter.setPen(QColor(80, 80, 80))
            painter.drawLine(10, y, self.width() - 10, y)
            y += 8
            painter.setFont(QFont("Microsoft YaHei", 10))
            for w in self._warnings[:5]:
                color = _COLORS.get(w.level, QColor(255, 255, 255))
                painter.setPen(color)
                icon = _ICONS.get(w.level.value, "?")
                painter.drawText(12, y + 12, f"{icon} {w.message}")
                y += 28

        painter.end()

    def _paint_v2_state(self, p: QPainter, y: int) -> int:
        """Paint V2 state with Goal/Context/Decisions."""
        si = self._state_info

        # Game time
        game_time = si.get("game_time", "")
        if game_time:
            p.setPen(QColor(255, 255, 255))
            p.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
            p.drawText(12, y + 14, f"⏱ {game_time}")
            p.setFont(QFont("Microsoft YaHei", 9))
            y += 24

        # Phase + Activity
        phase = _PHASE_CN.get(si.get("phase", ""), "?")
        activity = _ACTIVITY_CN.get(si.get("activity", ""), "?")
        p.setPen(QColor(200, 200, 200))
        p.drawText(12, y + 12, f"阶段: {phase}  活动: {activity}")
        y += 22

        # Combat + Threat
        combat = _COMBAT_CN.get(si.get("combat", ""), "?")
        threat = _THREAT_CN.get(si.get("threat", "low"), "?")
        threat_color = _THREAT_COLOR.get(si.get("threat", "low"), QColor(200, 200, 200))
        p.setPen(QColor(200, 200, 200))
        p.drawText(12, y + 12, f"战斗: {combat}  威胁: ")
        # Draw threat with color
        threat_x = 12 + p.fontMetrics().horizontalAdvance(f"战斗: {combat}  威胁: ")
        p.setPen(threat_color)
        p.drawText(threat_x, y + 12, threat)
        y += 22

        # Context
        context = _CONTEXT_CN.get(si.get("context", ""), "")
        if context:
            p.setPen(QColor(180, 200, 220))
            p.drawText(12, y + 12, f"场景: {context}")
            y += 22

        # Goal + Decisions
        goal_type = si.get("goal_type", "")
        goal_conf = si.get("goal_confidence", 0.0)
        if goal_type:
            goal_cn = _GOAL_CN.get(goal_type, goal_type)
            p.setPen(_GOAL_COLOR)
            p.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
            p.drawText(12, y + 14, f"★ 目标: {goal_cn} ({goal_conf:.0%})")
            p.setFont(QFont("Microsoft YaHei", 9))
            y += 26

        # Decisions (top 3)
        decisions = self._decisions[:3]
        if decisions:
            p.setPen(_DECISION_COLOR)
            for d in decisions:
                action = d.get("action", "") if isinstance(d, dict) else getattr(d, "action", "")
                score = d.get("score", 0) if isinstance(d, dict) else getattr(d, "score", 0)
                reason = d.get("reason", "") if isinstance(d, dict) else getattr(d, "reason", "")
                p.drawText(12, y + 12, f"→ {action} ({score:.0f}) {reason}")
                y += 22
            y += 6

        # KDA + Gold + Level
        kda = si.get("kda", "0/0/0")
        gold = si.get("gold", 0)
        level = si.get("level", 1)
        p.setPen(QColor(200, 200, 200))
        p.drawText(12, y + 12, f"KDA: {kda}  金: {gold}  等级: {level}")
        y += 22

        # Objectives
        obj_parts = []
        for key, label in [("dragon_spawn_in", "小龙"), ("baron_spawn_in", "男爵"), ("herald_spawn_in", "先锋")]:
            v = si.get(key, -1)
            if 0 <= v <= 120:
                obj_parts.append(f"{label}: {int(v)}s")
        if obj_parts:
            p.setPen(QColor(255, 200, 50))
            p.drawText(12, y + 12, "  ".join(obj_parts))
            y += 22

        # LLM Advice
        advice = si.get("advice", "")
        if advice:
            p.setPen(QColor(120, 220, 120))
            # Truncate long advice to fit width
            max_chars = 28
            display = advice[:max_chars] + "..." if len(advice) > max_chars else advice
            p.drawText(12, y + 12, f"💬 {display}")
            y += 28

        return y


class OverlayUI:
    """High-level overlay controller running in background thread."""

    def __init__(self, x: int = 1500, y: int = 50, width: int = 320, v2: bool = False) -> None:
        self._x = x
        self._y = y
        self._width = width
        self._v2 = v2
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
        if self._v2:
            self._widget = OverlayWidgetV2(self._x, self._y, self._width)
        else:
            self._widget = OverlayWidget(self._x, self._y, self._width)
        self._signals = _Signals()
        self._signals.state_updated.connect(self._widget.update_state)
        self._signals.warnings_updated.connect(self._widget.set_warnings)
        if self._v2:
            self._signals.decisions_updated.connect(self._widget.set_decisions)
        self._widget.show()
        self._app.exec_()

    def update_state(self, state_info: dict) -> None:
        if self._signals:
            self._signals.state_updated.emit(state_info)

    def update_warnings(self, warnings: List[Warning]) -> None:
        if self._signals:
            self._signals.warnings_updated.emit(warnings)

    def update_decisions(self, decisions: list) -> None:
        if self._signals and self._v2:
            self._signals.decisions_updated.emit(decisions)

    def stop(self) -> None:
        self._running = False
        if self._app:
            self._app.quit()

    @property
    def is_running(self) -> bool:
        return self._running
