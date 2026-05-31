"""Decision Engine — context-aware tactical warnings and suggestions.

20 rules across 5 categories, producing two levels of output:
- Level 1 (Alert): Time-sensitive warnings that need immediate attention
- Level 2 (Suggestion): Tactical advice based on current context
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from memory.temporal_memory import TemporalMemory
from models.game_state import GameState


class WarningLevel(str, Enum):
    INFO = "info"
    WARN = "warn"
    DANGER = "danger"
    SUGGEST = "suggest"


class RuleCategory(str, Enum):
    THREAT = "threat"
    OBJECTIVE = "objective"
    COMBAT = "combat"
    LANE = "lane"
    ECONOMY = "economy"


@dataclass
class Warning:
    """A tactical warning or suggestion."""
    level: WarningLevel
    message: str
    rule_name: str
    category: RuleCategory
    is_suggestion: bool = False
    timestamp: float = 0.0

    def __hash__(self):
        return hash((self.rule_name, self.message))


class RuleEngine:
    """20-rule Decision Engine with context awareness.

    Args:
        jungler_missing_threshold: Seconds for jungler missing warning.
        multi_missing_threshold: Number of missing enemies for group warning.
        dragon_warn_seconds: Seconds before dragon spawn.
        baron_warn_seconds: Seconds before baron spawn.
        teamfight_threshold: Combat probability threshold.
    """

    def __init__(
        self,
        jungler_missing_threshold: float = 20.0,
        multi_missing_threshold: int = 3,
        dragon_warn_seconds: float = 60.0,
        baron_warn_seconds: float = 90.0,
        teamfight_threshold: float = 0.5,
    ) -> None:
        self._jg_threshold = jungler_missing_threshold
        self._multi_threshold = multi_missing_threshold
        self._dragon_warn = dragon_warn_seconds
        self._baron_warn = baron_warn_seconds
        self._teamfight_threshold = teamfight_threshold
        self._recent_warnings: dict[str, float] = {}  # rule_name -> last_time
        self._dedup_seconds: float = 30.0

    def evaluate(
        self, state: GameState, memory: TemporalMemory
    ) -> List[Warning]:
        """Evaluate all rules and return warnings + suggestions."""
        now = state.current_time
        self._cleanup_dedup(now)

        alerts = self._evaluate_alerts(state, memory)
        suggestions = self._evaluate_suggestions(state, memory)

        # Filter duplicates
        alerts = self._filter_dedup(alerts, now)
        suggestions = self._filter_dedup(suggestions, now)

        return alerts + suggestions

    def _cleanup_dedup(self, now: float) -> None:
        """Remove entries older than dedup window."""
        self._recent_warnings = {
            k: v for k, v in self._recent_warnings.items()
            if now - v < self._dedup_seconds
        }

    def _filter_dedup(
        self, warnings: List[Warning], now: float
    ) -> List[Warning]:
        """Filter out recently shown warnings."""
        result = []
        for w in warnings:
            if w.rule_name not in self._recent_warnings:
                self._recent_warnings[w.rule_name] = now
                result.append(w)
        return result

    # ========== Level 1: Alerts (Time-sensitive warnings) ==========

    def _evaluate_alerts(
        self, state: GameState, memory: TemporalMemory
    ) -> List[Warning]:
        alerts = []
        for rule in [
            self._rule_jungler_missing,
            self._rule_multi_missing,
            self._rule_ambush_risk,
            self._rule_dragon_spawn,
            self._rule_herald_spawn,
            self._rule_baron_spawn,
            self._rule_dragon_fight_proximity,
            self._rule_baron_fight_proximity,
            self._rule_low_hp,
            self._rule_low_mana,
        ]:
            w = rule(state, memory)
            if w:
                alerts.append(w)
        return alerts

    def _rule_jungler_missing(self, state, memory):
        duration = memory.get_jungler_missing_duration()
        if duration >= self._jg_threshold:
            level = WarningLevel.DANGER if duration >= 30 else WarningLevel.WARN
            return Warning(level=level, rule_name="jungler_missing",
                message=f"敌方打野已消失 {int(duration)} 秒",
                category=RuleCategory.THREAT, timestamp=state.current_time)
        return None

    def _rule_multi_missing(self, state, memory):
        missing = memory.get_enemy_missing()
        if len(missing) >= self._multi_threshold:
            return Warning(level=WarningLevel.DANGER, rule_name="multi_missing",
                message=f"敌方 {len(missing)} 人消失，可能正在集结！",
                category=RuleCategory.THREAT, timestamp=state.current_time)
        return None

    def _rule_ambush_risk(self, state, memory):
        """Enemy split push + many missing = ambush risk."""
        if state.activity == "roaming" and state.threat_level in ("medium", "high"):
            return Warning(level=WarningLevel.WARN, rule_name="ambush_risk",
                message="你正在游走且敌方多人消失，小心被包夹！",
                    category=RuleCategory.THREAT, timestamp=state.current_time)
        return None

    def _rule_dragon_spawn(self, state, memory):
        if state.dragon_spawn_in >= 0 and state.dragon_spawn_in <= self._dragon_warn:
            return Warning(level=WarningLevel.WARN, rule_name="dragon_spawn",
                message=f"小龙将在 {int(state.dragon_spawn_in)} 秒后刷新",
                category=RuleCategory.OBJECTIVE, timestamp=state.current_time)
        return None

    def _rule_herald_spawn(self, state, memory):
        if state.herald_spawn_in >= 0 and state.herald_spawn_in <= 60:
            return Warning(level=WarningLevel.WARN, rule_name="herald_spawn",
                message=f"峡谷先锋将在 {int(state.herald_spawn_in)} 秒后刷新",
                category=RuleCategory.OBJECTIVE, timestamp=state.current_time)
        return None

    def _rule_baron_spawn(self, state, memory):
        if state.baron_spawn_in >= 0 and state.baron_spawn_in <= self._baron_warn:
            return Warning(level=WarningLevel.WARN, rule_name="baron_spawn",
                message=f"男爵将在 {int(state.baron_spawn_in)} 秒后刷新",
                category=RuleCategory.OBJECTIVE, timestamp=state.current_time)
        return None

    def _rule_dragon_fight_proximity(self, state, memory):
        if state.activity == "objective" and state.dragon.alive:
            return Warning(level=WarningLevel.WARN, rule_name="dragon_fight_proximity",
                message="正在争夺小龙，注意团战位置",
                category=RuleCategory.OBJECTIVE, timestamp=state.current_time)
        return None

    def _rule_baron_fight_proximity(self, state, memory):
        if state.activity == "objective":
            return Warning(level=WarningLevel.WARN, rule_name="baron_fight_proximity",
                message="男爵团正在发生，注意团战位置",
                category=RuleCategory.OBJECTIVE, timestamp=state.current_time)
        return None

    def _rule_low_hp(self, state, memory):
        if 0 < state.player_hp <= 25:
            return Warning(level=WarningLevel.DANGER, rule_name="low_hp",
                message=f"血量过低（{int(state.player_hp)}%），建议回城",
                category=RuleCategory.COMBAT, timestamp=state.current_time)
        return None

    def _rule_low_mana(self, state, memory):
        if 0 < state.player_mana <= 15 and state.player_hp > 30:
            return Warning(level=WarningLevel.WARN, rule_name="low_mana",
                message=f"蓝量不足（{int(state.player_mana)}%），注意技能管理",
                category=RuleCategory.COMBAT, timestamp=state.current_time)
        return None

    # ========== Level 2: Suggestions (Context-aware advice) ==========

    def _evaluate_suggestions(
        self, state: GameState, memory: TemporalMemory
    ) -> List[Warning]:
        suggestions = []
        for rule in [
            self._sug_laning_advantage,
            self._sug_laning_disadvantage,
            self._sug_dragon_advantage,
            self._sug_dragon_disadvantage,
            self._sug_retreat_split_push,
            self._sug_lane_pressure,
            self._sug_level_lead,
            self._sug_level_behind,
            self._sug_gold_lead,
            self._sug_teamfight_advantage,
        ]:
            w = rule(state, memory)
            if w:
                suggestions.append(w)
        return suggestions

    def _sug_laning_advantage(self, state, memory):
        if (state.activity in ("laning", "skirmish")
                and state.combat_state == "advantage"):
            return Warning(level=WarningLevel.SUGGEST, rule_name="sug_lane_adv",
                message="对线优势，建议积极换血",
                category=RuleCategory.COMBAT, is_suggestion=True,
                timestamp=state.current_time)
        return None

    def _sug_laning_disadvantage(self, state, memory):
        if (state.activity in ("laning", "skirmish")
                and state.combat_state == "disadvantage"):
            return Warning(level=WarningLevel.SUGGEST, rule_name="sug_lane_disadv",
                message="对线劣势，建议稳健补刀",
                category=RuleCategory.COMBAT, is_suggestion=True,
                timestamp=state.current_time)
        return None

    def _sug_dragon_advantage(self, state, memory):
        if (state.activity == "objective"
                and state.combat_state == "advantage"):
            return Warning(level=WarningLevel.SUGGEST, rule_name="sug_dragon_adv",
                message="我方优势，建议争夺小龙",
                category=RuleCategory.OBJECTIVE, is_suggestion=True,
                timestamp=state.current_time)
        return None

    def _sug_dragon_disadvantage(self, state, memory):
        if (state.activity == "objective"
                and state.combat_state == "disadvantage"):
            return Warning(level=WarningLevel.SUGGEST, rule_name="sug_dragon_disadv",
                message="我方劣势，建议放龙换资源",
                category=RuleCategory.OBJECTIVE, is_suggestion=True,
                timestamp=state.current_time)
        return None

    def _sug_retreat_split_push(self, state, memory):
        if (state.activity == "roaming"
                and state.threat_level in ("medium", "high")):
            return Warning(level=WarningLevel.SUGGEST, rule_name="sug_retreat_sp",
                message="带线风险高，建议后撤",
                category=RuleCategory.THREAT, is_suggestion=True,
                timestamp=state.current_time)
        return None

    def _sug_lane_pressure(self, state, memory):
        if state.lane_state == "being_pushed":
            return Warning(level=WarningLevel.SUGGEST, rule_name="sug_lane_pressure",
                message="兵线被推，建议回防清线",
                category=RuleCategory.LANE, is_suggestion=True,
                timestamp=state.current_time)
        return None

    def _sug_level_lead(self, state, memory):
        if state.player_level >= 11 and state.game_phase == "mid_game":
            return Warning(level=WarningLevel.INFO, rule_name="sug_level_lead",
                message=f"等级 {state.player_level}，可以主动寻找机会",
                category=RuleCategory.ECONOMY, is_suggestion=True,
                timestamp=state.current_time)
        return None

    def _sug_level_behind(self, state, memory):
        if state.player_level <= 7 and state.game_phase == "mid_game":
            return Warning(level=WarningLevel.SUGGEST, rule_name="sug_level_behind",
                message="等级落后，建议保守发育",
                category=RuleCategory.ECONOMY, is_suggestion=True,
                timestamp=state.current_time)
        return None

    def _sug_gold_lead(self, state, memory):
        if state.current_gold >= 15000 and state.game_phase in ("mid_game", "late_game"):
            return Warning(level=WarningLevel.INFO, rule_name="sug_gold_lead",
                message="经济充裕，注意更新装备",
                category=RuleCategory.ECONOMY, is_suggestion=True,
                timestamp=state.current_time)
        return None

    def _sug_teamfight_advantage(self, state, memory):
        if (state.activity == "teamfight"
                and state.combat_state == "advantage"):
            return Warning(level=WarningLevel.SUGGEST, rule_name="sug_tf_adv",
                message="团战我方优势，可以主动开团",
                category=RuleCategory.COMBAT, is_suggestion=True,
                timestamp=state.current_time)
        return None

    # ========== Legacy interface (backward compatible) ==========

    def clear_recent(self) -> None:
        """Clear dedup cache."""
        self._recent_warnings.clear()
