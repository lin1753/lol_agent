"""Objective Memory — tracks neutral objective kill/respawn times.

2025/2026 LOL objective timing:

Lower Pit (Dragon Pit):
- Dragon: 5:00 first spawn, 5:00 respawn
- Elder Dragon: spawns after Dragon Soul, 10:00 respawn

Upper Pit (Baron Pit):
- Voidgrubs: 5:00 first spawn (3 grubs, once per game)
- Herald: 8:00 spawn (once per game, despawns at 19:30)
- Baron: 25:00 first spawn, 6:00 respawn
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# LOL 2025/2026 objective timing constants (seconds)
DRAGON_FIRST_SPAWN = 300     # 5:00
DRAGON_RESPAWN = 300         # 5 minutes
GRUB_FIRST_SPAWN = 300       # 5:00 (once per game, 3 grubs)
HERALD_FIRST_SPAWN = 480     # 8:00 (once per game)
HERALD_DESPAWN = 1170        # 19:30
BARON_FIRST_SPAWN = 1500     # 25:00
BARON_RESPAWN = 360          # 6 minutes
ELDER_RESPAWN = 600          # 10 minutes (spawns after Dragon Soul)


@dataclass
class ObjectiveRecord:
    """Record for a single objective."""
    name: str
    alive: bool = True
    last_killed_time: Optional[float] = None
    kill_count: int = 0


class ObjectiveMemory:
    """Tracks objective kill times and computes respawn timers.

    Upper Pit (Baron Pit): herald, grub, baron
    Lower Pit (Dragon Pit): dragon, elder

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
            "elder": ObjectiveRecord(name="elder"),
        }
        self._dragon_soul_claimed = False

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

    def set_dragon_soul_claimed(self) -> None:
        """Mark that Dragon Soul has been claimed (triggers Elder Dragon)."""
        self._dragon_soul_claimed = True

    def get_spawn_timers(self, current_time: float) -> dict[str, float]:
        """Compute seconds until next spawn for each objective.

        Returns dict with negative = unknown/not applicable.
        """
        timers = {}

        # Dragon (Lower Pit)
        timers["dragon_spawn_in"] = self._compute_timer(
            self._objectives["dragon"], current_time,
            DRAGON_FIRST_SPAWN, DRAGON_RESPAWN,
        )

        # Elder Dragon (Lower Pit) — only after Dragon Soul
        if self._dragon_soul_claimed:
            timers["elder_spawn_in"] = self._compute_timer(
                self._objectives["elder"], current_time,
                0,  # first spawn is immediate after soul
                ELDER_RESPAWN,
            )
        else:
            timers["elder_spawn_in"] = -1.0

        # Voidgrubs (Upper Pit) — spawns once at 5:00, no respawn
        grub_rec = self._objectives["grub"]
        if grub_rec.alive:
            if current_time < GRUB_FIRST_SPAWN:
                timers["grub_spawn_in"] = GRUB_FIRST_SPAWN - current_time
            else:
                timers["grub_spawn_in"] = 0.0  # Already spawned
        else:
            timers["grub_spawn_in"] = -1.0  # Dead, no respawn

        # Herald (Upper Pit) — 8:00 once, despawns 19:30
        rec = self._objectives["herald"]
        if rec.alive:
            if current_time < HERALD_FIRST_SPAWN:
                timers["herald_spawn_in"] = HERALD_FIRST_SPAWN - current_time
            elif current_time <= HERALD_DESPAWN:
                timers["herald_spawn_in"] = 0.0  # Available
            else:
                timers["herald_spawn_in"] = -1.0  # Past despawn
        else:
            # Dead, once per game — no respawn
            timers["herald_spawn_in"] = -1.0

        # Baron (Upper Pit)
        timers["baron_spawn_in"] = self._compute_timer(
            self._objectives["baron"], current_time,
            BARON_FIRST_SPAWN, BARON_RESPAWN,
        )

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
        self._dragon_soul_claimed = False

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
