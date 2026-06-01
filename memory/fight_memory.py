"""Fight Memory — tracks recent teamfight and death events."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FightRecord:
    """Record of a teamfight or skirmish."""
    time: float
    result: str  # "won", "lost", "ongoing"
    ally_count: int = 0
    enemy_count: int = 0
    location: str = ""  # "top", "mid", "bot", "jungle"


@dataclass
class DeathRecord:
    """Record of a player death."""
    time: float
    killer: str = ""  # hero name or "tower", "minion", etc.
    location: str = ""


class FightMemory:
    """Tracks recent fight and death events for pattern recognition.

    Args:
        max_fights: Maximum fight records to keep.
        max_deaths: Maximum death records to keep.
    """

    def __init__(self, max_fights: int = 20, max_deaths: int = 20) -> None:
        self._fights: deque[FightRecord] = deque(maxlen=max_fights)
        self._deaths: deque[DeathRecord] = deque(maxlen=max_deaths)

    def record_fight(
        self,
        time: float,
        result: str,
        ally_count: int = 0,
        enemy_count: int = 0,
        location: str = "",
    ) -> None:
        """Record a teamfight event."""
        self._fights.append(FightRecord(
            time=time, result=result,
            ally_count=ally_count, enemy_count=enemy_count,
            location=location,
        ))

    def record_death(self, time: float, killer: str = "", location: str = "") -> None:
        """Record a player death."""
        self._deaths.append(DeathRecord(
            time=time, killer=killer, location=location,
        ))

    def get_recent_fights(self, n: int = 5) -> List[FightRecord]:
        """Get the N most recent fights."""
        return list(self._fights)[-n:]

    def get_recent_deaths(self, n: int = 5) -> List[DeathRecord]:
        """Get the N most recent deaths."""
        return list(self._deaths)[-n:]

    def get_fight_win_rate(self, last_n: int = 10) -> float:
        """Compute win rate of recent fights (0~1)."""
        fights = list(self._fights)[-last_n:]
        if not fights:
            return 0.5  # Unknown
        wins = sum(1 for f in fights if f.result == "won")
        return wins / len(fights)

    def get_death_count_since(self, since_time: float) -> int:
        """Count deaths since a given time."""
        return sum(1 for d in self._deaths if d.time >= since_time)

    def clear(self) -> None:
        """Reset all fight memory."""
        self._fights.clear()
        self._deaths.clear()
