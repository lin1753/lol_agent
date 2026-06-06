"""Goal Engine — determines the current strategic objective.

9 goal types:
    contest_dragon / contest_baron / contest_herald
    push_tower / defend_tower / split_push
    group / retreat / reset
"""

from __future__ import annotations

from memory.temporal_memory import TemporalMemory
from schemas.feature_bundle import FeatureBundle
from schemas.goal import Goal
from schemas.state import GameStateV2


class GoalEngine:
    """Determine the current strategic goal.

    Each goal has a priority score; the highest wins.
    Confidence reflects how strongly the goal is recommended (0~1).

    Usage:
        engine = GoalEngine()
        goal = engine.determine(state, features, memory)
    """

    def determine(
        self,
        state: GameStateV2,
        features: FeatureBundle,
        memory: TemporalMemory,
    ) -> Goal:
        """Determine the best strategic goal.

        Args:
            state: Current GameStateV2.
            features: Current FeatureBundle.
            memory: TemporalMemory for hero tracking.

        Returns:
            Goal with goal_type and confidence.
        """
        candidates = []

        # --- Objective goals ---
        if features.objective.dragon_alive and 0 <= state.dragon_spawn_in <= 90:
            score = self._score_contest_objective(state, features, "dragon")
            candidates.append(Goal(goal_type="contest_dragon", confidence=score))

        if features.objective.baron_alive and 0 <= state.baron_spawn_in <= 120:
            score = self._score_contest_objective(state, features, "baron")
            candidates.append(Goal(goal_type="contest_baron", confidence=score))

        if features.objective.herald_alive and 0 <= state.herald_spawn_in <= 60:
            score = self._score_contest_objective(state, features, "herald")
            candidates.append(Goal(goal_type="contest_herald", confidence=score))

        # --- Combat goals ---
        if state.combat == "advantage" and features.hero.ally_count >= 3:
            score = min(0.7 + features.hero.ally_count * 0.05, 0.95)
            # Ult ready is critical for group fights
            if features.skill.ult_ready:
                score += 0.1
            else:
                score -= 0.1
            # HP ratio bonus
            hp = features.hero.hp_ratio
            if hp > 0.2:
                score += 0.05
            candidates.append(Goal(goal_type="group", confidence=min(score, 1.0)))

        if state.threat == "high" or state.combat == "disadvantage":
            score = 0.8 if state.threat == "high" else 0.6
            # HP ratio amplifies retreat urgency
            hp = features.hero.hp_ratio
            if hp < -0.3:
                score += 0.1
            if not features.skill.flash_ready:
                score += 0.05
            candidates.append(Goal(goal_type="retreat", confidence=min(score, 1.0)))

        # --- Map control goals ---
        if (features.wave.wave_strength > 0.3
                and features.map.enemy_missing >= 2
                and state.phase != "early"):
            score = min(0.5 + features.wave.wave_strength * 0.3, 0.85)
            candidates.append(Goal(goal_type="push_tower", confidence=score))

        if (features.wave.enemy_minions >= 5
                and features.hero.enemy_count >= 2):
            score = min(0.5 + features.wave.enemy_minions * 0.05, 0.8)
            candidates.append(Goal(goal_type="defend_tower", confidence=score))

        if (state.phase in ("mid", "late")
                and features.hero.ally_count >= 3
                and features.map.enemy_missing >= 2):
            score = 0.5
            candidates.append(Goal(goal_type="split_push", confidence=score))

        # --- Default: reset ---
        if not candidates:
            candidates.append(Goal(goal_type="reset", confidence=0.3))

        # Return highest confidence goal
        return max(candidates, key=lambda g: g.confidence)

    @staticmethod
    def _score_contest_objective(
        state: GameStateV2,
        features: FeatureBundle,
        obj_type: str,
    ) -> float:
        """Score how favorable contesting an objective is."""
        score = 0.5  # Base score for objective being available

        # Combat advantage bonus
        if state.combat == "advantage":
            score += 0.25
        elif state.combat == "disadvantage":
            score -= 0.2

        # Number advantage bonus
        if features.hero.ally_count > features.hero.enemy_count:
            score += 0.15
        elif features.hero.enemy_count > features.hero.ally_count:
            score -= 0.1

        # HP ratio bonus (more granular than combat string)
        hp = features.hero.hp_ratio
        if hp > 0.3:
            score += 0.1
        elif hp < -0.3:
            score -= 0.1

        # Ult ready for objective fight
        if features.skill.ult_ready:
            score += 0.05

        # Urgency: closer spawn = higher score
        if obj_type == "dragon" and 0 <= state.dragon_spawn_in <= 30:
            score += 0.1
        elif obj_type == "baron" and 0 <= state.baron_spawn_in <= 30:
            score += 0.1

        # Baron is more important in late game
        if obj_type == "baron" and state.phase == "late":
            score += 0.1

        return max(0.0, min(1.0, score))
