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
    """V2 overlay — redesigned with proper sections.

    Layout:
    ┌─────────────────────────────┐
    │ LOL Agent V2    12:34  30FPS│  ← header
    │ OCR: ✓  YOLO: ✓            │  ← status
    │─────────────────────────────│
    │ KDA: 5/2/8  金: 12000      │  ← player stats
    │ 等级: 14  HP: +0.3         │
    │ 大招: ✓  闪现: ✓           │
    │─────────────────────────────│
    │ 阶段: 中期  场景: 争夺     │  ← game state
    │ 战斗: 优势  威胁: 低       │
    │ 人数: 3v2                   │
    │─────────────────────────────│
    │ ★ 目标: 争夺小龙 (91%)     │  ← tactical
    │ → 争夺小龙 (95) 人数3v2    │
    │ → 布控视野 (50) 提前准备   │
    │─────────────────────────────│
    │ ⚠ 小龙: 30s  男爵: 60s    │  ← objectives
    │─────────────────────────────│
    │ ▲ 敌方打野消失 30 秒       │  ← warnings
    │ 💬 建议控制视野后开龙      │  ← LLM
    └─────────────────────────────┘
    """

    def __init__(self, x: int = 1500, y: int = 50, width: int = 340) -> None:
        super().__init__(x, y, width)
        self._decisions: list = []

    def set_decisions(self, decisions: list) -> None:
        self._decisions = list(decisions)
        self._auto_resize()
        self.update()

    def _trunc(self, painter: QPainter, text: str, max_width: int) -> str:
        """Truncate text to fit within max_width pixels."""
        if painter.fontMetrics().horizontalAdvance(text) <= max_width:
            return text
        while len(text) > 1 and painter.fontMetrics().horizontalAdvance(text + "..") > max_width:
            text = text[:-1]
        return text + ".."

    def _auto_resize(self) -> None:
        n_warn = len(self._warnings)
        n_dec = min(len(self._decisions), 3)
        si = self._state_info
        has_state = bool(si)

        # Count active objectives
        active_obj = 0
        if has_state:
            for key in ("dragon_spawn_in", "baron_spawn_in", "herald_spawn_in"):
                v = si.get(key, -1)
                if 0 <= v <= 120:
                    active_obj += 1

        # Calculate height per section
        height = 10
        # Header: title + time/fps row
        height += 28 + 20
        # Status row
        height += 20

        if has_state:
            # Player stats: KDA row + level/HP row + skills row
            height += 6 + 20 + 20 + 20
            # Game state: phase/context + combat/threat + count
            height += 6 + 20 + 20 + 20
            # Goal
            if si.get("goal_type"):
                height += 6 + 26
            # Decisions
            if n_dec > 0:
                height += n_dec * 20
            # Objectives
            if active_obj > 0:
                height += 6 + 20

        # Warnings
        if n_warn > 0:
            height += 6 + min(n_warn, 5) * 22
        # Advice
        if si and si.get("advice"):
            height += 22

        height = max(80, height) + 10
        pos = self.pos()
        self.setGeometry(pos.x(), pos.y(), self._width, height)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 8, 8)
        painter.fillPath(path, QColor(0, 0, 0, 190))

        y = 10
        si = self._state_info
        w = self._width - 24  # usable width

        # === HEADER ===
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        painter.drawText(12, y + 12, "LOL Agent V2")
        # Game time + FPS on right side
        game_time = si.get("game_time", "") if si else ""
        fps = si.get("fps", 0) if si else 0
        if game_time:
            right_text = game_time
            painter.setFont(QFont("Microsoft YaHei", 10))
            rx = w - painter.fontMetrics().horizontalAdvance(right_text) + 12
            painter.drawText(rx, y + 12, right_text)
        y += 28

        # Status row
        if si:
            ocr_ok = si.get("ocr_ready", False)
            painter.setFont(QFont("Microsoft YaHei", 8))
            painter.setPen(QColor(100, 220, 100) if ocr_ok else QColor(255, 150, 50))
            ocr_text = f"OCR: {'✓' if ocr_ok else '✗'}"
            painter.drawText(12, y + 10, ocr_text)
            painter.setPen(QColor(100, 220, 100))
            painter.drawText(80, y + 10, "YOLO: ✓")
            y += 20

        if not si:
            painter.end()
            return

        # === Divider helper ===
        def divider():
            nonlocal y
            painter.setPen(QColor(60, 60, 60))
            painter.drawLine(10, y, self._width - 10, y)
            y += 6

        # === PLAYER STATS ===
        divider()
        painter.setFont(QFont("Microsoft YaHei", 9))

        # KDA
        kda = si.get("kda", "")
        kda_display = kda if kda else "--/--/--"
        has_kda = si.get("has_kda", False)
        painter.setPen(QColor(255, 255, 255) if has_kda else QColor(120, 120, 120))
        painter.drawText(12, y + 12, f"KDA: {kda_display}")

        # Gold
        gold = si.get("gold", 0)
        has_gold = si.get("has_gold", False)
        gold_display = str(gold) if has_gold and gold > 0 else "--"
        painter.setPen(QColor(255, 215, 0) if has_gold and gold > 0 else QColor(120, 120, 120))
        gx = 12 + painter.fontMetrics().horizontalAdvance(f"KDA: {kda_display}  ")
        painter.drawText(gx, y + 12, f"金: {gold_display}")
        y += 20

        # Level + HP ratio
        level = si.get("level", 1)
        level_display = str(level) if level > 1 else "--"
        hp_ratio = si.get("hp_ratio", 0.0)
        hp_color = QColor(100, 220, 100) if hp_ratio > 0.1 else (QColor(255, 80, 80) if hp_ratio < -0.1 else QColor(200, 200, 200))
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(12, y + 12, f"等级: {level_display}  HP:")
        hp_x = 12 + painter.fontMetrics().horizontalAdvance(f"等级: {level_display}  HP: ")
        painter.setPen(hp_color)
        hp_sign = "+" if hp_ratio > 0 else ""
        painter.drawText(hp_x, y + 12, f"{hp_sign}{hp_ratio:.1f}")
        y += 20

        # Skills
        ult = si.get("ult_ready", False)
        flash = si.get("flash_ready", False)
        painter.setPen(QColor(100, 220, 100) if ult else QColor(255, 80, 80))
        painter.drawText(12, y + 12, f"大招: {'✓' if ult else '✗'}")
        painter.setPen(QColor(100, 220, 100) if flash else QColor(255, 80, 80))
        painter.drawText(100, y + 12, f"闪现: {'✓' if flash else '✗'}")
        y += 20

        # === GAME STATE ===
        divider()
        painter.setFont(QFont("Microsoft YaHei", 9))

        # Phase + Context
        phase = _PHASE_CN.get(si.get("phase", ""), "?")
        context = _CONTEXT_CN.get(si.get("context", ""), "?")
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(12, y + 12, f"阶段: {phase}  场景: {context}")
        y += 20

        # Combat + Threat
        combat = _COMBAT_CN.get(si.get("combat", ""), "?")
        threat = _THREAT_CN.get(si.get("threat", "low"), "?")
        threat_color = _THREAT_COLOR.get(si.get("threat", "low"), QColor(200, 200, 200))
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(12, y + 12, f"战斗: {combat}  威胁: ")
        threat_x = 12 + painter.fontMetrics().horizontalAdvance(f"战斗: {combat}  威胁: ")
        painter.setPen(threat_color)
        painter.drawText(threat_x, y + 12, threat)
        y += 20

        # Hero counts
        ally_n = si.get("ally_count", 0)
        enemy_n = si.get("enemy_count", 0)
        count_color = QColor(100, 220, 100) if ally_n > enemy_n else (QColor(255, 80, 80) if ally_n < enemy_n else QColor(200, 200, 200))
        painter.setPen(count_color)
        painter.drawText(12, y + 12, f"人数: {ally_n}v{enemy_n}")
        y += 20

        # === TACTICAL ===
        goal_type = si.get("goal_type", "")
        if goal_type:
            divider()
            painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
            goal_cn = _GOAL_CN.get(goal_type, goal_type)
            goal_conf = si.get("goal_confidence", 0.0)
            painter.setPen(_GOAL_COLOR)
            painter.drawText(12, y + 14, f"★ {goal_cn} ({goal_conf:.0%})")
            painter.setFont(QFont("Microsoft YaHei", 9))
            y += 26

        # Decisions (top 3)
        decisions = self._decisions[:3]
        if decisions:
            painter.setPen(_DECISION_COLOR)
            for d in decisions:
                action = d.get("action", "") if isinstance(d, dict) else getattr(d, "action", "")
                score = d.get("score", 0) if isinstance(d, dict) else getattr(d, "score", 0)
                reason = d.get("reason", "") if isinstance(d, dict) else getattr(d, "reason", "")
                raw = f"→ {action} ({score:.0f}) {reason}"
                painter.drawText(12, y + 12, self._trunc(painter, raw, w))
                y += 20

        # === OBJECTIVES (upper/lower pit grouping) ===
        def _fmt_timer(v):
            """Smart timer format: only show within 2 min countdown.
            ≤120s → M:SS, >120s → None (don't show)"""
            if v < 0 or v > 120:
                return None
            m, s = divmod(int(v), 60)
            return f"{m}:{s:02d}"

        # Lower Pit (Dragon Pit): dragon, elder
        lower_parts = []
        for key, label in [("dragon_spawn_in", "龙"), ("elder_spawn_in", "远古")]:
            v = si.get(key, -1)
            t = _fmt_timer(v)
            if t:
                lower_parts.append(f"{label} {t}")

        # Upper Pit (Baron Pit): grub, herald (once per game), baron
        upper_parts = []
        # Grub: only show if alive (once per game)
        grub_v = si.get("grub_spawn_in", -1)
        grub_t = _fmt_timer(grub_v)
        if grub_t and grub_v >= 0:
            upper_parts.append(f"虫 {grub_t}")
        # Herald: only show if alive (once per game)
        herald_v = si.get("herald_spawn_in", -1)
        herald_t = _fmt_timer(herald_v)
        if herald_t and herald_v >= 0:
            upper_parts.append(f"先锋 {herald_t}")
        # Baron: always show if timer valid
        baron_v = si.get("baron_spawn_in", -1)
        baron_t = _fmt_timer(baron_v)
        if baron_t:
            upper_parts.append(f"男爵 {baron_t}")

        if lower_parts or upper_parts:
            divider()
            painter.setFont(QFont("Microsoft YaHei", 9))
            if lower_parts:
                painter.setPen(QColor(100, 180, 255))
                painter.drawText(12, y + 12, "下河道: " + "  ".join(lower_parts))
                y += 20
            if upper_parts:
                painter.setPen(QColor(255, 180, 100))
                painter.drawText(12, y + 12, "上河道: " + "  ".join(upper_parts))
                y += 20

        # === WARNINGS ===
        if self._warnings:
            divider()
            painter.setFont(QFont("Microsoft YaHei", 9))
            for w in self._warnings[:5]:
                color = _COLORS.get(w.level, QColor(255, 255, 255))
                painter.setPen(color)
                icon = _ICONS.get(w.level.value, "?")
                raw = f"{icon} {w.message}"
                painter.drawText(12, y + 12, self._trunc(painter, raw, w))
                y += 22

        # === LLM ADVICE ===
        advice = si.get("advice", "")
        if advice:
            painter.setPen(QColor(120, 220, 120))
            painter.setFont(QFont("Microsoft YaHei", 9))
            raw = f"💬 {advice}"
            painter.drawText(12, y + 12, self._trunc(painter, raw, w))
            y += 22

        painter.end()


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
