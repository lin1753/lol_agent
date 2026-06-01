"""Objective Memory — tracks neutral objective kill/respawn times."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# LOL objective timing constants (seconds)
DRAGON_FIRST_SPAWN = 300     # 5:00
DRAGON_RESPAWN = 300         # 5 minutes
BARON_FIRST_SPAWN = 1200     # 20:00
BARON_RESPAWN = 360          # 6 minutes
HERALD_FIRST_SPAWN = 480     # 8:00
HERALD_DESPAWN = 660         # 11:00
HERALD_RESPAWN = 240         # 4 minutes
GRUB_FIRST_SPAWN = 480       # 8:00 (same as herald)


@dataclass
class ObjectiveRecord:
    """Record for a single objective."""
    name: str
    alive: bool = True
    last_killed_time: Optional[float] = None
    kill_count: int = 0


class ObjectiveMemory:
    """Tracks objective kill times and computes respawn timers.

    Usage:
        mem = ObjectiveMemory()
        mem.record_kill("dragon", game_time=600)
        timers = mem.get_spawn_timers(current_time=650)
    """

    def __init__(self) -> None:
        self._objectives = {
            "dragon": ObjectiveRecord(name="dragon"),
            "baron": ObjectiveRecord(name="baron"),
            "herald": ObjectiveRecord(name="herald"),
            "grub": ObjectiveRecord(name="grub"),
        }

    def record_kill(self, objective: str, game_time: float) -> None:
        """Record that an objective was killed at game_time."""
        if objective in self._objectives:
            rec = self._objectives[objective]
            rec.alive = False
            rec.last_killed_time = game_time
            rec.kill_count += 1

    def record_spawn(self, objective: str) -> None:
        """Record that an objective has spawned (detected alive)."""
        if objective in self._objectives:
            self._objectives[objective].alive = True

    def get_spawn_timers(self, current_time: float) -> dict[str, float]:
        """Compute seconds until next spawn for each objective.

        Returns dict with negative = unknown/not applicable.
        """
        timers = {}

        # Dragon
        timers["dragon_spawn_in"] = self._compute_timer(
            self._objectives["dragon"], current_time,
            DRAGON_FIRST_SPAWN, DRAGON_RESPAWN,
        )

        # Baron
        timers["baron_spawn_in"] = self._compute_timer(
            self._objectives["baron"], current_time,
            BARON_FIRST_SPAWN, BARON_RESPAWN,
        )

        # Herald
        rec = self._objectives["herald"]
        if rec.alive:
            if HERALD_FIRST_SPAWN <= current_time <= HERALD_DESPAWN:
                time_since = current_time - HERALD_FIRST_SPAWN
                timers["herald_spawn_in"] = HERALD_RESPAWN - (time_since % HERALD_RESPAWN)
            elif current_time < HERALD_FIRST_SPAWN:
                timers["herald_spawn_in"] = HERALD_FIRST_SPAWN - current_time
            else:
                timers["herald_spawn_in"] = -1.0  # Past despawn
        elif rec.last_killed_time is not None:
            remaining = HERALD_RESPAWN - (current_time - rec.last_killed_time)
            if current_time < HERALD_DESPAWN:
                timers["herald_spawn_in"] = max(0, remaining)
            else:
                timers["herald_spawn_in"] = -1.0
        else:
            timers["herald_spawn_in"] = -1.0

        return timers

    def get_objective(self, name: str) -> Optional[ObjectiveRecord]:
        """Get record for a specific objective."""
        return self._objectives.get(name)

    def clear(self) -> None:
        """Reset all objective memory."""
        for rec in self._objectives.values():
            rec.alive = True
            rec.last_killed_time = None
            rec.kill_count = 0

    @staticmethod
    def _compute_timer(
        rec: ObjectiveRecord,
        current_time: float,
        first_spawn: float,
        respawn: float,
    ) -> float:
        """Compute spawn timer for a standard objective."""
        if rec.alive:
            if current_time < first_spawn:
                return first_spawn - current_time
            time_since_first = current_time - first_spawn
            return respawn - (time_since_first % respawn)
        elif rec.last_killed_time is not None:
            return max(0, respawn - (current_time - rec.last_killed_time))
        return -1.0
