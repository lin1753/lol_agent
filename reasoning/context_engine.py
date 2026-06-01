"""Context Engine — determines the current situation context.

7 context types representing the tactical situation:
    safe_farm / pressure / siege / defense / contest / collapse / retreat
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
        # 1. retreat: high threat + combat disadvantage
        if state.threat == "high" and state.combat == "disadvantage":
            return "retreat"

        # 2. collapse: enemy 3+ pushing toward base (enemy minions at high count near towers)
        if (features.wave.enemy_minions >= 6
                and features.hero.enemy_count >= 3
                and features.hero.ally_count <= 2):
            return "collapse"

        # 3. contest: objective about to spawn + both sides nearby
        objective_near = (
            (0 <= state.dragon_spawn_in <= 60)
            or (0 <= state.baron_spawn_in <= 90)
            or (0 <= state.herald_spawn_in <= 60)
        )
        if objective_near and features.hero.ally_count >= 2 and features.hero.enemy_count >= 2:
            return "contest"

        # 4. siege: multiple allies near enemy tower (pushing + ally advantage)
        if (features.wave.ally_minions >= 4
                and features.hero.ally_count >= 3
                and features.hero.enemy_count <= 2):
            return "siege"

        # 5. defense: enemies pushing into our territory
        if (features.wave.enemy_minions >= 4
                and features.hero.enemy_count >= 2
                and features.hero.ally_count <= 2):
            return "defense"

        # 6. pressure: lane advantage + enemies missing (we can push)
        if (features.wave.wave_strength > 0.2
                and features.map.enemy_missing >= 2
                and state.threat != "high"):
            return "pressure"

        # 7. safe_farm: default
        return "safe_farm"
