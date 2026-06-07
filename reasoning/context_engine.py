"""Context Engine — determines the current situation context.

7 context types representing the tactical situation:
    safe_farm / pressure / siege / defense / contest / collapse / retreat

Based on LOL macro strategy principles:
- Game phase matters (early safe_farm is normal, late is wasteful)
- Objective alive status matters, not just spawn timers
- HP ratio and skill readiness factor into decisions
- Missing enemies = danger, not just a number
"""

from __future__ import annotations

from memory.temporal_memory import TemporalMemory
from schemas.feature_bundle import FeatureBundle
from schemas.state import GameStateV2


CONTEXT_TYPES = [
    "safe_farm",
    "pressure",
    "siege",
    "defense",
    "contest",
    "collapse",
    "retreat",
]


class ContextEngine:
    """Determine the current situation context.

    Priority (highest first):
        retreat > collapse > contest > siege > defense > pressure > safe_farm

    Usage:
        engine = ContextEngine()
        context = engine.compute(features, state, memory)
    """

    def compute(
        self,
        features: FeatureBundle,
        state: GameStateV2,
        memory: TemporalMemory,
    ) -> str:
        """Compute context from features, state, and memory.

        Args:
            features: Current frame's FeatureBundle.
            state: Current GameStateV2 (phase/activity/combat/threat).
            memory: TemporalMemory for missing hero tracking.

        Returns:
            One of the 7 context type strings.
        """
        hp = features.hero.hp_ratio
        ally = features.hero.ally_count
        enemy = features.hero.enemy_count
        missing = features.map.enemy_missing
        phase = state.phase

        # 1. retreat: critical danger
        # - HP < 30% (ratio < -0.4 means significantly more enemy HP)
        # - Outnumbered 2+ with no flash
        # - High threat + combat disadvantage
        if hp < -0.4:
            return "retreat"
        if state.threat == "high" and state.combat == "disadvantage":
            return "retreat"
        if enemy >= ally + 2 and not features.skill.flash_ready:
            return "retreat"

        # 2. collapse: enemy hard push toward base
        # - Enemy wave ≥ 4 with 2+ enemies, few allies defending
        # - Relaxed from original (was enemy≥3 AND minions≥6 AND ally≤2)
        if (features.wave.enemy_minions >= 4
                and enemy >= 2
                and ally <= enemy - 1):
            return "collapse"

        # 3. contest: objective control situation
        # - Dragon/baron/herald alive AND (fighting nearby OR spawning soon)
        # - Both sides have presence
        objective_alive = (
            features.objective.dragon_alive
            or features.objective.baron_alive
            or features.objective.herald_alive
        )
        objective_soon = (
            (0 <= state.dragon_spawn_in <= 60)
            or (0 <= state.baron_spawn_in <= 90)
            or (0 <= state.herald_spawn_in <= 60)
        )
        # Contest if: objective alive AND we have numbers AND enemies nearby
        if objective_alive and ally >= 2 and enemy >= 1:
            # Higher priority if spawning soon or enemies also contesting
            if objective_soon or enemy >= 2:
                return "contest"
        # Also contest if spawning very soon and both sides gathering
        if objective_soon and ally >= 2 and enemy >= 2:
            return "contest"

        # 4. siege: pushing with advantage
        # - Ally minions pushing + number advantage
        # - Can safely pressure tower
        if (features.wave.ally_minions >= 3
                and ally >= enemy
                and ally >= 2):
            return "siege"

        # 5. defense: enemy pushing toward our towers
        # - Enemy minions ≥ 3 with enemy heroes present
        if (features.wave.enemy_minions >= 3
                and enemy >= 1
                and enemy >= ally):
            return "defense"

        # 6. pressure: lane advantage, can push safely
        # - Wave pushing + enemies missing (they're elsewhere)
        # - Safe to extend
        if (features.wave.wave_strength > 0.2
                and missing >= 2
                and state.threat != "high"):
            return "pressure"

        # 7. safe_farm: default
        # Note: In late game, safe_farm is suboptimal (should group/objective)
        # but we still return it - GoalEngine will override with better goals
        return "safe_farm"
