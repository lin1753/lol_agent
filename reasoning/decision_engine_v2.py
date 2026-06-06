"""Decision Engine V2 — Goal-driven candidate actions with scoring.

Unlike V1 RuleEngine (20 rules → Warning list), V2 produces a ranked
list of Decision candidates driven by the current Goal.
"""

from __future__ import annotations

from typing import List

from memory.temporal_memory import TemporalMemory
from schemas.decision import Decision
from schemas.feature_bundle import FeatureBundle
from schemas.goal import Goal
from schemas.state import GameStateV2


class DecisionEngineV2:
    """Goal-driven Decision Engine.

    Selects relevant rules based on goal_type, scores each candidate,
    and returns a sorted Decision list.

    Usage:
        engine = DecisionEngineV2()
        decisions = engine.evaluate(state, goal, features, memory)
    """

    def evaluate(
        self,
        state: GameStateV2,
        goal: Goal,
        features: FeatureBundle,
        memory: TemporalMemory,
    ) -> List[Decision]:
        """Produce ranked candidate decisions.

        Args:
            state: Current GameStateV2.
            goal: Current strategic Goal from GoalEngine.
            features: Current FeatureBundle.
            memory: TemporalMemory.

        Returns:
            List of Decision sorted by score (descending).
        """
        decisions: List[Decision] = []

        # Goal-specific rules
        goal_rules = _GOAL_RULES.get(goal.goal_type, [])
        for rule_fn in goal_rules:
            d = rule_fn(state, goal, features, memory)
            if d is not None:
                decisions.append(d)

        # Universal rules (always evaluated)
        for rule_fn in _UNIVERSAL_RULES:
            d = rule_fn(state, goal, features, memory)
            if d is not None:
                decisions.append(d)

        # Sort by score descending
        decisions.sort(key=lambda d: d.score, reverse=True)
        return decisions


# ========== Goal-specific rule sets ==========


def _rule_contest_dragon(state, goal, features, memory):
    """Recommend contesting dragon."""
    if not features.objective.dragon_alive:
        return None
    score = 60.0
    if state.combat == "advantage":
        score += 20.0
    if features.hero.ally_count > features.hero.enemy_count:
        score += 10.0
    if 0 <= state.dragon_spawn_in <= 30:
        score += 10.0
    # HP ratio bonus
    hp = features.hero.hp_ratio
    if hp > 0.3:
        score += 5.0
    elif hp < -0.3:
        score -= 10.0
    # Ult ready bonus
    if features.skill.ult_ready:
        score += 5.0
    return Decision(action="contest_dragon", score=min(max(score, 0), 100.0),
                    reason=_reason("小龙争夺", state, features))


def _rule_contest_baron(state, goal, features, memory):
    """Recommend contesting baron."""
    if not features.objective.baron_alive:
        return None
    score = 65.0
    if state.combat == "advantage":
        score += 20.0
    if features.hero.ally_count > features.hero.enemy_count:
        score += 10.0
    if state.phase == "late":
        score += 10.0
    hp = features.hero.hp_ratio
    if hp > 0.3:
        score += 5.0
    elif hp < -0.3:
        score -= 10.0
    if features.skill.ult_ready:
        score += 5.0
    return Decision(action="contest_baron", score=min(max(score, 0), 100.0),
                    reason=_reason("男爵争夺", state, features))


def _rule_contest_herald(state, goal, features, memory):
    """Recommend contesting herald."""
    if not features.objective.herald_alive:
        return None
    score = 50.0
    if state.combat == "advantage":
        score += 15.0
    if features.hero.ally_count >= features.hero.enemy_count:
        score += 10.0
    return Decision(action="contest_herald", score=min(score, 100.0),
                    reason=_reason("先锋争夺", state, features))


def _rule_push_tower(state, goal, features, memory):
    """Recommend pushing tower."""
    score = 55.0 + features.wave.wave_strength * 20.0
    if features.map.enemy_missing >= 2:
        score += 10.0
    if state.combat == "advantage":
        score += 10.0
    return Decision(action="push_tower", score=min(max(score, 0), 100.0),
                    reason="兵线优势，可以推塔")


def _rule_defend_tower(state, goal, features, memory):
    """Recommend defending tower."""
    score = 60.0
    if features.wave.enemy_minions >= 5:
        score += 15.0
    if features.hero.enemy_count >= 3:
        score += 10.0
    return Decision(action="defend_tower", score=min(score, 100.0),
                    reason="敌方推线，需要回防")


def _rule_split_push(state, goal, features, memory):
    """Recommend split push."""
    score = 45.0
    if features.map.enemy_missing >= 2:
        score += 15.0
    if state.combat == "even":
        score += 5.0
    return Decision(action="split_push", score=min(score, 100.0),
                    reason="侧面分推，牵制敌方")


def _rule_group_fight(state, goal, features, memory):
    """Recommend grouping for teamfight."""
    score = 55.0
    if features.hero.ally_count >= 4:
        score += 20.0
    if state.combat == "advantage":
        score += 15.0
    # Ult ready is critical for teamfight
    if features.skill.ult_ready:
        score += 10.0
    else:
        score -= 10.0  # No ult = risky to fight
    # HP ratio
    hp = features.hero.hp_ratio
    if hp > 0.2:
        score += 5.0
    elif hp < -0.2:
        score -= 10.0
    return Decision(action="group", score=min(max(score, 0), 100.0),
                    reason="人数优势，建议集合团战" if features.hero.ally_count >= 4 else "建议集合团战")


def _rule_retreat(state, goal, features, memory):
    """Recommend retreating."""
    score = 70.0
    if state.threat == "high":
        score += 15.0
    if state.combat == "disadvantage":
        score += 10.0
    if features.hero.enemy_count > features.hero.ally_count + 1:
        score += 10.0
    # No flash = higher urgency to retreat early
    if not features.skill.flash_ready:
        score += 5.0
    # HP ratio
    hp = features.hero.hp_ratio
    if hp < -0.3:
        score += 10.0
    reason = "局势不利，建议后撤"
    if not features.skill.flash_ready:
        reason += "（无闪现）"
    return Decision(action="retreat", score=min(score, 100.0), reason=reason)


def _rule_reset(state, goal, features, memory):
    """Recommend reset (recall)."""
    score = 40.0
    return Decision(action="reset", score=score, reason="状态不佳，建议回城")


# ========== Universal rules (always evaluated) ==========


def _rule_low_hp_warning(state, goal, features, memory):
    """Low HP → suggest retreat regardless of goal."""
    hp = features.hero.hp_ratio
    # HP ratio < -0.4 means significantly more enemy HP
    if hp < -0.4 or state.threat == "high":
        return Decision(action="retreat", score=85.0,
                        reason="血量劣势，建议回城")
    return None


def _rule_missing_enemies_warning(state, goal, features, memory):
    """Multiple enemies missing → caution."""
    if features.map.enemy_missing >= 3:
        return Decision(action="play_safe", score=60.0,
                        reason=f"敌方 {features.map.enemy_missing} 人消失，注意安全")
    return None


def _rule_objective_timer_warning(state, goal, features, memory):
    """Objective about to spawn → prepare."""
    if 0 <= state.dragon_spawn_in <= 30 and features.objective.dragon_alive:
        return Decision(action="prepare_dragon", score=55.0,
                        reason=f"小龙 {int(state.dragon_spawn_in)}s 后刷新，准备视野")
    if 0 <= state.baron_spawn_in <= 30 and features.objective.baron_alive:
        return Decision(action="prepare_baron", score=60.0,
                        reason=f"男爵 {int(state.baron_spawn_in)}s 后刷新，准备视野")
    return None


# ========== Rule registry ==========

_GOAL_RULES: dict[str, list] = {
    "contest_dragon": [_rule_contest_dragon],
    "contest_baron": [_rule_contest_baron],
    "contest_herald": [_rule_contest_herald],
    "push_tower": [_rule_push_tower],
    "defend_tower": [_rule_defend_tower],
    "split_push": [_rule_split_push],
    "group": [_rule_group_fight],
    "retreat": [_rule_retreat],
    "reset": [_rule_reset],
}

_UNIVERSAL_RULES: list = [
    _rule_low_hp_warning,
    _rule_missing_enemies_warning,
    _rule_objective_timer_warning,
]


# ========== Helpers ==========


def _reason(label: str, state: GameStateV2, features: FeatureBundle) -> str:
    """Build a human-readable reason string."""
    parts = [label]
    if state.combat == "advantage":
        parts.append("我方优势")
    elif state.combat == "disadvantage":
        parts.append("我方劣势")
    if features.hero.ally_count > features.hero.enemy_count:
        parts.append(f"人数 {features.hero.ally_count}v{features.hero.enemy_count}")
    return "，".join(parts)
