"""Goal Engine — determines the current strategic objective.

9 goal types:
    contest_dragon / contest_baron / contest_herald
    push_tower / defend_tower / split_push
    group / retreat / farm

Key LOL strategy principles:
- Objective alive = always worth considering (not just spawn timer)
- Even numbers + ult ready = can fight (not just advantage)
- Missing enemies = danger for pushing
- Game phase changes priorities (early=farm, mid=objectives, late=baron/group)
- HP ratio matters more than binary combat state
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
        """Determine the best strategic goal."""
        candidates = []

        hp = features.hero.hp_ratio
        ally = features.hero.ally_count
        enemy = features.hero.enemy_count
        missing = features.map.enemy_missing
        phase = state.phase

        # === OBJECTIVE GOALS ===
        # Dragon: always consider if alive (not just spawn timer)
        if features.objective.dragon_alive:
            score = self._score_objective(state, features, "dragon")
            candidates.append(Goal(goal_type="contest_dragon", confidence=score))

        # Baron: critical in mid/late game
        if features.objective.baron_alive:
            score = self._score_objective(state, features, "baron")
            candidates.append(Goal(goal_type="contest_baron", confidence=score))

        # Herald: valuable early-mid for tower plates
        if features.objective.herald_alive and phase != "late":
            score = self._score_objective(state, features, "herald")
            candidates.append(Goal(goal_type="contest_herald", confidence=score))

        # === COMBAT GOALS ===
        # Group: can fight if numbers even or better, especially with ult
        if ally >= 2:
            score = 0.4  # Base
            # Number advantage
            if ally > enemy:
                score += 0.2
            elif ally == enemy:
                # Even numbers: can fight if ult ready
                if features.skill.ult_ready:
                    score += 0.15
                else:
                    score -= 0.1
            else:
                score -= 0.2  # Outnumbered

            # HP advantage
            if hp > 0.2:
                score += 0.1
            elif hp < -0.2:
                score -= 0.15

            # Phase bonus: grouping more important in mid/late
            if phase in ("mid", "late"):
                score += 0.1

            # Combat state bonus
            if state.combat == "advantage":
                score += 0.15
            elif state.combat == "disadvantage":
                score -= 0.15

            if score > 0.3:
                candidates.append(Goal(goal_type="group", confidence=min(score, 1.0)))

        # Retreat: danger situation
        if state.threat == "high" or state.combat == "disadvantage" or hp < -0.3:
            score = 0.6
            if state.threat == "high":
                score += 0.15
            if hp < -0.3:
                score += 0.1
            if not features.skill.flash_ready:
                score += 0.05
            if enemy > ally + 1:
                score += 0.1
            candidates.append(Goal(goal_type="retreat", confidence=min(score, 1.0)))

        # === MAP CONTROL GOALS ===
        # Push tower: wave advantage + enemies elsewhere
        if (features.wave.wave_strength > 0.2
                and missing >= 1
                and state.threat != "high"):
            score = 0.4 + features.wave.wave_strength * 0.3
            if missing >= 3:
                score += 0.1  # Very safe to push
            if ally >= 2:
                score += 0.1
            if phase != "early":
                score += 0.05  # Towers worth more after plates
            candidates.append(Goal(goal_type="push_tower", confidence=min(score, 1.0)))

        # Defend tower: enemy wave incoming
        if features.wave.enemy_minions >= 3 and enemy >= 1:
            score = 0.5 + features.wave.enemy_minions * 0.03
            if enemy >= 3:
                score += 0.1  # Serious push
            candidates.append(Goal(goal_type="defend_tower", confidence=min(score, 0.9)))

        # Split push: mid/late, allies can hold, enemies elsewhere
        if (phase in ("mid", "late")
                and missing >= 2
                and ally >= 2):  # Allies can hold 4v3
            score = 0.35
            if missing >= 3:
                score += 0.15
            candidates.append(Goal(goal_type="split_push", confidence=min(score, 0.85)))

        # === DEFAULT: farm ===
        if not candidates:
            score = 0.3
            if phase == "early":
                score = 0.5  # Farming is perfectly fine early
            candidates.append(Goal(goal_type="farm", confidence=score))

        return max(candidates, key=lambda g: g.confidence)

    @staticmethod
    def _score_objective(
        state: GameStateV2,
        features: FeatureBundle,
        obj_type: str,
    ) -> float:
        """Score how favorable contesting/taking an objective is."""
        hp = features.hero.hp_ratio
        ally = features.hero.ally_count
        enemy = features.hero.enemy_count

        score = 0.45  # Base: objective is available

        # Number advantage (most important for objectives)
        if ally > enemy:
            score += 0.2
        elif ally == enemy:
            score += 0.05
        elif ally < enemy:
            score -= 0.15

        # HP ratio
        if hp > 0.3:
            score += 0.1
        elif hp < -0.3:
            score -= 0.1

        # Ult ready for objective fight
        if features.skill.ult_ready:
            score += 0.05

        # Spawn urgency (closer = more urgent)
        spawn_key = f"{obj_type}_spawn_in"
        spawn_in = getattr(state, spawn_key, -1)
        if 0 <= spawn_in <= 30:
            score += 0.15  # Very soon!
        elif 0 <= spawn_in <= 60:
            score += 0.05

        # Phase importance
        if obj_type == "baron" and state.phase == "late":
            score += 0.15  # Baron is game-winning late
        elif obj_type == "dragon" and state.phase == "mid":
            score += 0.05  # Dragon soul point approaching
        elif obj_type == "herald" and state.phase == "early":
            score += 0.05  # Herald for plates

        # Enemy missing = risk of steal/gank
        if features.map.enemy_missing >= 3:
            score -= 0.1

        return max(0.0, min(1.0, score))
