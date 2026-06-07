"""Decision Engine V2 — Goal-driven candidate actions with scoring.

Key improvements over V1:
- Each goal maps to MULTIPLE candidate rules (not just 1)
- Actions are deduplicated (no duplicate "retreat")
- Reasons include specific numbers (HP ratio, counts, skill status)
- Universal rules fill gaps without duplicating goal-specific ones

LOL strategy rules applied:
- Objective contest: numbers + HP + ult + vision all matter
- Teamfight: ult readiness is critical, even numbers can fight with ult
- Split push: needs allies to hold 4v5, enemies elsewhere
- Retreat: HP < 30%, outnumbered, no flash, high threat
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
    deduplicates actions, and returns a sorted Decision list.

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
        """Produce ranked candidate decisions."""
        decisions: List[Decision] = []

        # Goal-specific rules (each goal has multiple candidates)
        goal_rules = _GOAL_RULES.get(goal.goal_type, [])
        for rule_fn in goal_rules:
            d = rule_fn(state, goal, features, memory)
            if d is not None:
                decisions.append(d)

        # Universal rules (fill gaps, don't duplicate)
        for rule_fn in _UNIVERSAL_RULES:
            d = rule_fn(state, goal, features, memory)
            if d is not None:
                decisions.append(d)

        # Deduplicate: keep highest score per action
        seen = {}
        for d in decisions:
            if d.action not in seen or d.score > seen[d.action].score:
                seen[d.action] = d
        decisions = list(seen.values())

        # Sort by score descending
        decisions.sort(key=lambda d: d.score, reverse=True)
        return decisions


# ========== Helper ==========


def _reason(parts: list[str]) -> str:
    """Build reason from parts, filtering empty."""
    return "，".join(p for p in parts if p)


# ========== Goal-specific rule sets ==========


# --- Contest Dragon ---
def _rule_contest_dragon_fight(state, goal, features, memory):
    """Primary: fight for dragon."""
    if not features.objective.dragon_alive:
        return None
    hp = features.hero.hp_ratio
    ally, enemy = features.hero.ally_count, features.hero.enemy_count
    score = 55.0
    parts = ["小龙争夺"]

    # Numbers
    if ally > enemy:
        score += 15.0
        parts.append(f"人数{ally}v{enemy}")
    elif ally == enemy:
        score += 5.0
    else:
        score -= 15.0
        parts.append(f"人数劣势{ally}v{enemy}")

    # Combat state
    if state.combat == "advantage":
        score += 15.0
        parts.append("战力优势")
    elif state.combat == "disadvantage":
        score -= 10.0

    # HP ratio
    if hp > 0.2:
        score += 5.0
    elif hp < -0.2:
        score -= 8.0
        parts.append("血量劣势")

    # Ult ready
    if features.skill.ult_ready:
        score += 5.0
        parts.append("大招就绪")

    # Spawn urgency
    if 0 <= state.dragon_spawn_in <= 30:
        score += 10.0

    return Decision(action="contest_dragon", score=min(max(score, 0), 100.0),
                    reason=_reason(parts))


def _rule_contest_dragon_vision(state, goal, features, memory):
    """Secondary: prepare vision for dragon."""
    if not features.objective.dragon_alive:
        return None
    if state.dragon_spawn_in < 0 or state.dragon_spawn_in > 60:
        return None
    score = 40.0 + state.dragon_spawn_in * 0.3
    return Decision(action="prepare_vision", score=min(score, 70.0),
                    reason=f"小龙{int(state.dragon_spawn_in)}s后刷新，提前布控视野")


def _rule_contest_dragon_pressure(state, goal, features, memory):
    """Tertiary: push lane to create pressure while dragon spawns."""
    if not features.objective.dragon_alive:
        return None
    if state.dragon_spawn_in < 0 or state.dragon_spawn_in > 45:
        return None
    if features.wave.wave_strength <= 0:
        return None
    score = 35.0 + features.wave.wave_strength * 15.0
    return Decision(action="push_lane_pressure", score=min(score, 60.0),
                    reason="推线制造压力，为小龙争夺创造优势")


# --- Contest Baron ---
def _rule_contest_baron_fight(state, goal, features, memory):
    """Primary: fight for baron."""
    if not features.objective.baron_alive:
        return None
    hp = features.hero.hp_ratio
    ally, enemy = features.hero.ally_count, features.hero.enemy_count
    score = 60.0
    parts = ["男爵争夺"]

    if ally > enemy:
        score += 15.0
        parts.append(f"人数{ally}v{enemy}")
    elif ally == enemy:
        score += 5.0
    else:
        score -= 15.0

    if state.combat == "advantage":
        score += 15.0
        parts.append("战力优势")
    elif state.combat == "disadvantage":
        score -= 10.0

    if hp > 0.2:
        score += 5.0
    elif hp < -0.2:
        score -= 8.0

    if features.skill.ult_ready:
        score += 5.0
        parts.append("大招就绪")

    if state.phase == "late":
        score += 10.0
        parts.append("后期关键")

    if 0 <= state.baron_spawn_in <= 30:
        score += 10.0

    return Decision(action="contest_baron", score=min(max(score, 0), 100.0),
                    reason=_reason(parts))


def _rule_contest_baron_sneak(state, goal, features, memory):
    """Sneak baron if enemies are far away."""
    if not features.objective.baron_alive:
        return None
    if features.map.enemy_missing < 3:
        return None  # Too risky if enemies visible
    if features.hero.ally_count < 3:
        return None
    score = 50.0
    if features.skill.ult_ready:
        score += 10.0
    if features.hero.hp_ratio > 0.2:
        score += 10.0
    return Decision(action="sneak_baron", score=min(score, 80.0),
                    reason="敌方多人消失，可尝试偷男爵")


# --- Contest Herald ---
def _rule_contest_herald(state, goal, features, memory):
    """Take herald."""
    if not features.objective.herald_alive:
        return None
    hp = features.hero.hp_ratio
    ally, enemy = features.hero.ally_count, features.hero.enemy_count
    score = 45.0
    parts = ["先锋争夺"]

    if ally >= enemy:
        score += 10.0
    else:
        score -= 10.0

    if hp > 0.2:
        score += 5.0

    if features.skill.ult_ready:
        score += 5.0

    return Decision(action="contest_herald", score=min(max(score, 0), 100.0),
                    reason=_reason(parts))


# --- Push Tower ---
def _rule_push_tower(state, goal, features, memory):
    """Push tower with wave advantage."""
    wave = features.wave.wave_strength
    if wave <= 0:
        return None
    score = 45.0 + wave * 25.0
    parts = ["推塔"]

    if features.map.enemy_missing >= 2:
        score += 10.0
        parts.append(f"敌方{features.map.enemy_missing}人消失")
    if state.combat == "advantage":
        score += 8.0
    if features.hero.ally_count >= 2:
        score += 5.0

    return Decision(action="push_tower", score=min(max(score, 0), 100.0),
                    reason=_reason(parts))


def _rule_push_tower_plates(state, goal, features, memory):
    """Push for tower plates (early game)."""
    if state.phase != "early":
        return None
    if features.wave.wave_strength <= 0.1:
        return None
    score = 50.0 + features.wave.wave_strength * 20.0
    if features.map.enemy_missing >= 1:
        score += 10.0
    return Decision(action="push_tower", score=min(score, 85.0),
                    reason="前期推塔拿镀层")


# --- Defend Tower ---
def _rule_defend_tower(state, goal, features, memory):
    """Defend against enemy push."""
    if features.wave.enemy_minions < 2:
        return None
    score = 50.0 + features.wave.enemy_minions * 5.0
    parts = ["回防清线"]

    if features.hero.enemy_count >= 2:
        score += 10.0
        parts.append(f"敌方{features.hero.enemy_count}人推进")
    if features.hero.ally_count < features.hero.enemy_count:
        score += 5.0  # More urgent if outnumbered

    return Decision(action="defend_tower", score=min(score, 95.0),
                    reason=_reason(parts))


# --- Split Push ---
def _rule_split_push(state, goal, features, memory):
    """Split push on side lane."""
    if state.phase == "early":
        return None
    if features.hero.ally_count < 2:
        return None  # Need allies to hold
    score = 40.0
    parts = ["分推"]

    if features.map.enemy_missing >= 2:
        score += 15.0
        parts.append("敌方注意力分散")
    if features.wave.wave_strength > 0:
        score += 10.0

    return Decision(action="split_push", score=min(score, 80.0),
                    reason=_reason(parts))


# --- Group ---
def _rule_group_fight(state, goal, features, memory):
    """Group for teamfight."""
    ally, enemy = features.hero.ally_count, features.hero.enemy_count
    if ally < 2:
        return None
    score = 45.0
    parts = ["集合团战"]

    if ally > enemy:
        score += 20.0
        parts.append(f"人数{ally}v{enemy}")
    elif ally == enemy:
        score += 5.0
        if features.skill.ult_ready:
            score += 15.0
            parts.append("大招就绪可打")
        else:
            score -= 10.0
    else:
        score -= 15.0

    hp = features.hero.hp_ratio
    if hp > 0.2:
        score += 5.0
    elif hp < -0.2:
        score -= 10.0

    if state.combat == "advantage":
        score += 10.0

    return Decision(action="group", score=min(max(score, 0), 100.0),
                    reason=_reason(parts))


# --- Retreat ---
def _rule_retreat(state, goal, features, memory):
    """Retreat from danger."""
    hp = features.hero.hp_ratio
    ally, enemy = features.hero.ally_count, features.hero.enemy_count
    score = 60.0
    parts = ["后撤"]

    if state.threat == "high":
        score += 15.0
        parts.append("高威胁")
    if state.combat == "disadvantage":
        score += 10.0
        parts.append("战力劣势")
    if hp < -0.3:
        score += 10.0
        parts.append("血量劣势")
    if enemy > ally + 1:
        score += 10.0
        parts.append(f"被{enemy}v{ally}包围")
    if not features.skill.flash_ready:
        score += 5.0
        parts.append("无闪现")

    return Decision(action="retreat", score=min(score, 100.0),
                    reason=_reason(parts))


# --- Farm (default) ---
def _rule_farm(state, goal, features, memory):
    """Farm/safe laning."""
    score = 35.0
    if state.phase == "early":
        score = 50.0  # Farming is great early
    elif state.phase == "mid":
        score = 35.0
    else:
        score = 20.0  # Late game farming is less valuable

    # Bonus if wave is pushing toward us (safe farm)
    if features.wave.wave_strength < 0:
        score += 5.0

    return Decision(action="farm", score=score, reason="安全发育补兵")


# ========== Universal rules (always evaluated, no duplicates) ==========


def _rule_critical_hp(state, goal, features, memory):
    """Critical HP: must recall regardless of goal."""
    hp = features.hero.hp_ratio
    if hp < -0.5:  # Very bad HP
        return Decision(action="recall", score=95.0,
                        reason="血量极低，必须回城")
    return None


def _rule_dangerous_missing(state, goal, features, memory):
    """Many enemies missing = high risk."""
    missing = features.map.enemy_missing
    if missing >= 4:
        return Decision(action="play_safe", score=70.0,
                        reason=f"敌方{missing}人消失，极度危险")
    if missing >= 3 and state.phase != "early":
        return Decision(action="play_safe", score=55.0,
                        reason=f"敌方{missing}人消失，注意视野")
    return None


def _rule_objective_prep(state, goal, features, memory):
    """Objective spawning soon → prepare."""
    if (features.objective.dragon_alive
            and 0 <= state.dragon_spawn_in <= 45
            and state.dragon_spawn_in > 15):
        return Decision(action="prepare_objective", score=50.0,
                        reason=f"小龙{int(state.dragon_spawn_in)}s后刷新，建议提前就位")
    if (features.objective.baron_alive
            and 0 <= state.baron_spawn_in <= 60
            and state.baron_spawn_in > 20):
        return Decision(action="prepare_objective", score=55.0,
                        reason=f"男爵{int(state.baron_spawn_in)}s后刷新，建议提前就位")
    return None


# ========== Rule registry ==========

_GOAL_RULES: dict[str, list] = {
    "contest_dragon": [_rule_contest_dragon_fight, _rule_contest_dragon_vision, _rule_contest_dragon_pressure],
    "contest_baron": [_rule_contest_baron_fight, _rule_contest_baron_sneak],
    "contest_herald": [_rule_contest_herald],
    "push_tower": [_rule_push_tower, _rule_push_tower_plates],
    "defend_tower": [_rule_defend_tower],
    "split_push": [_rule_split_push],
    "group": [_rule_group_fight],
    "retreat": [_rule_retreat],
    "farm": [_rule_farm],
}

_UNIVERSAL_RULES: list = [
    _rule_critical_hp,
    _rule_dangerous_missing,
    _rule_objective_prep,
]
