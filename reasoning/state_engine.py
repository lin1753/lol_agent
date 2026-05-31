"""State Understanding Engine — transforms raw game data into high-level state.

Computes game_phase, context, combat_state, lane_state, threat_level,
and objective timers from GameState + TemporalMemory.

6 sub-engines, each independent and composable.
"""

from __future__ import annotations

from typing import Optional

from models.game_state import GameState, HeroPosition, Team
from memory.temporal_memory import TemporalMemory


# --- LOL objective timing (seconds) ---
DRAGON_FIRST_SPAWN = 300  # 5:00
DRAGON_RESPAWN = 300       # 5 minutes
HERALD_FIRST_SPAWN = 480   # 8:00
HERALD_DESPAWN = 660       # 11:00
HERALD_RESPAWN = 240       # 4 minutes
BARON_FIRST_SPAWN = 1200   # 20:00
BARON_RESPAWN = 360        # 6 minutes


def compute_game_phase(current_time: float) -> str:
    """Determine game phase based on time."""
    minutes = current_time / 60
    if minutes < 14:
        return "early_game"
    elif minutes < 25:
        return "mid_game"
    else:
        return "late_game"


def compute_context(
    state: GameState,
    memory: TemporalMemory,
) -> str:
    """Determine the current game context/situation."""
    total_visible = state.enemy_count_visible + state.ally_count_visible
    missing = memory.get_enemy_missing()
    missing_count = len(missing)

    # Objective fights
    if state.dragon.alive and state.teamfight_probability > 0.4:
        # Check if heroes are near dragon area (minimap positions)
        return "dragon_fight"
    if state.baron.alive and state.teamfight_probability > 0.4:
        return "baron_fight"

    # Teamfight (both sides 3+ visible and clustered)
    if state.enemy_count_visible >= 3 and state.ally_count_visible >= 3:
        if state.teamfight_probability >= 0.5:
            return "teamfight"

    # Skirmish (2-4 from each side)
    if 2 <= state.enemy_count_visible <= 4 and 2 <= state.ally_count_visible <= 4:
        return "skirmish"

    # Split push (player alone, no nearby enemies)
    if state.ally_count_visible <= 1 and state.enemy_count_visible <= 1:
        if missing_count >= 2:
            return "split_push"

    # Default: laning
    return "laning"


def compute_combat_state(
    state: GameState,
    memory: TemporalMemory,
) -> tuple[str, float]:
    """Evaluate combat advantage based on count, levels, HP.

    Returns (combat_state, combat_score).
    """
    score = 0.0

    # Factor 1: Numbers advantage (weight: 0.4)
    ally_count = state.ally_count_visible + 1  # +1 for player
    enemy_count = state.enemy_count_visible + 1
    if ally_count > enemy_count:
        score += 0.4 * min((ally_count - enemy_count) / 3, 1.0)
    elif enemy_count > ally_count:
        score -= 0.4 * min((enemy_count - ally_count) / 3, 1.0)

    # Factor 2: HP advantage (weight: 0.3)
    if state.player_hp > 0:
        hp_ratio = state.player_hp / 100
        if hp_ratio > 0.7:
            score += 0.3 * (hp_ratio - 0.5)
        elif hp_ratio < 0.3:
            score -= 0.3 * (0.5 - hp_ratio)

    # Factor 3: Missing enemies reduce safety (weight: 0.3)
    missing = memory.get_enemy_missing()
    if len(missing) >= 3:
        score -= 0.3
    elif len(missing) >= 2:
        score -= 0.15
    elif len(missing) == 0 and state.enemy_count_visible >= 2:
        score += 0.1  # Visible enemies are less threatening than unknown

    # Clamp
    score = max(-1.0, min(1.0, score))

    if score > 0.2:
        return "advantage", score
    elif score < -0.2:
        return "disadvantage", score
    else:
        return "even", score


def compute_lane_state(state: GameState) -> str:
    """Evaluate lane state based on minion/tower counts."""
    # Red minions pushing into blue = being_pushed (for our team)
    red_pressure = state.red_minion_count + state.red_cannon_count * 2
    blue_pressure = state.blue_minion_count + state.blue_cannon_count * 2

    # Tower advantage
    if state.red_towers_alive < state.blue_towers_alive:
        red_pressure += 1  # Red side losing towers → blue pushing
    elif state.blue_towers_alive < state.red_towers_alive:
        blue_pressure += 1

    if red_pressure > blue_pressure + 2:
        return "being_pushed"
    elif blue_pressure > red_pressure + 2:
        return "pushing"
    else:
        return "neutral"


def compute_threat_level(
    state: GameState,
    memory: TemporalMemory,
) -> str:
    """Evaluate overall threat level."""
    threat_score = 0

    # Missing enemies
    missing = memory.get_enemy_missing()
    if len(missing) >= 3:
        threat_score += 3
    elif len(missing) >= 2:
        threat_score += 2
    elif len(missing) >= 1:
        threat_score += 1

    # Missing jungler specifically
    jungler_duration = memory.get_jungler_missing_duration()
    if jungler_duration >= 30:
        threat_score += 2
    elif jungler_duration >= 15:
        threat_score += 1

    # Low HP
    if state.player_hp < 30:
        threat_score += 1

    # Danger lane
    if state.danger_lane:
        threat_score += 1

    if threat_score >= 4:
        return "high"
    elif threat_score >= 2:
        return "medium"
    else:
        return "low"


def compute_objective_timers(state: GameState) -> dict[str, float]:
    """Compute seconds until next spawn for each objective.

    Uses LOL game timing knowledge. Returns dict with negative = unknown.
    """
    t = state.current_time
    timers = {"dragon_spawn_in": -1.0, "baron_spawn_in": -1.0, "herald_spawn_in": -1.0}

    # Dragon: first spawn at 5:00, respawns every 5 min after kill
    if state.dragon.alive:
        if t < DRAGON_FIRST_SPAWN:
            timers["dragon_spawn_in"] = DRAGON_FIRST_SPAWN - t
        else:
            # Timer counting up from last spawn
            time_since_first = t - DRAGON_FIRST_SPAWN
            time_to_next = DRAGON_RESPAWN - (time_since_first % DRAGON_RESPAWN)
            timers["dragon_spawn_in"] = time_to_next
    elif state.dragon.last_killed_time is not None:
        timers["dragon_spawn_in"] = max(0, DRAGON_RESPAWN - (t - state.dragon.last_killed_time))

    # Baron: spawns at 20:00, respawns every 6 min
    if state.baron.alive:
        if t < BARON_FIRST_SPAWN:
            timers["baron_spawn_in"] = BARON_FIRST_SPAWN - t
        else:
            time_since_first = t - BARON_FIRST_SPAWN
            time_to_next = BARON_RESPAWN - (time_since_first % BARON_RESPAWN)
            timers["baron_spawn_in"] = time_to_next
    elif state.baron.last_killed_time is not None:
        timers["baron_spawn_in"] = max(0, BARON_RESPAWN - (t - state.baron.last_killed_time))

    # Herald: 8:00-11:00 only, respawn 4 min
    if state.herald.alive:
        if HERALD_FIRST_SPAWN <= t <= HERALD_DESPAWN:
            time_since_first = t - HERALD_FIRST_SPAWN
            time_to_next = HERALD_RESPAWN - (time_since_first % HERALD_RESPAWN)
            timers["herald_spawn_in"] = time_to_next
        elif t < HERALD_FIRST_SPAWN:
            timers["herald_spawn_in"] = HERALD_FIRST_SPAWN - t
    elif state.herald.last_killed_time is not None:
        timers["herald_spawn_in"] = max(0, HERALD_RESPAWN - (t - state.herald.last_killed_time))

    return timers


class StateEngine:
    """State Understanding Engine — combines all 6 sub-engines.

    Usage:
        engine = StateEngine()
        state = engine.understand(state, memory)
    """

    def understand(
        self, state: GameState, memory: TemporalMemory
    ) -> GameState:
        """Enrich GameState with state understanding fields.

        Modifies state in-place and returns it.

        Args:
            state: Current game state from StateParser.
            memory: Temporal memory with history.

        Returns:
            Enriched GameState with phase/context/combat/lane/threat/timers.
        """
        # 1. Game Phase
        state.game_phase = compute_game_phase(state.current_time)

        # 2. Context
        state.context = compute_context(state, memory)

        # 3. Combat
        state.combat_state, state.combat_score = compute_combat_state(state, memory)

        # 4. Lane
        state.lane_state = compute_lane_state(state)

        # 5. Threat
        state.threat_level = compute_threat_level(state, memory)

        # 6. Objective Timers
        timers = compute_objective_timers(state)
        state.dragon_spawn_in = timers["dragon_spawn_in"]
        state.baron_spawn_in = timers["baron_spawn_in"]
        state.herald_spawn_in = timers["herald_spawn_in"]

        return state
