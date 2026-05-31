"""Temporal Memory — maintains historical game state for agent-level reasoning.

This is what makes the system an "Agent" rather than a simple CV pipeline.
It tracks per-hero last-seen times and positions, computes missing durations,
and maintains a rolling window of recent states.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from models.game_state import GameState, HeroPosition, Team


@dataclass
class HeroMemory:
    """Historical record for a single hero."""

    name: str
    team: Team
    last_seen_time: float = 0.0
    last_position: tuple[float, float] = (0.0, 0.0)
    last_lane: Optional[str] = None
    missing_duration: float = 0.0
    trajectory: list[tuple[float, float, float]] = field(
        default_factory=list
    )  # [(time, x, y), ...]


class TemporalMemory:
    """Maintains temporal history of game state.

    Tracks per-hero last-seen information, computes missing durations,
    and stores a rolling window of recent GameState snapshots.

    Args:
        window_size: Number of recent states to keep (default: 30).
    """

    def __init__(self, window_size: int = 30) -> None:
        self._window_size = window_size
        self._history: deque[GameState] = deque(maxlen=window_size)
        self._hero_memory: Dict[str, HeroMemory] = {}
        self._current_time: float = 0.0

    def update(self, state: GameState) -> None:
        """Update memory with a new GameState.

        Should be called once per frame.

        Args:
            state: Current game state from StateParser.
        """
        self._current_time = state.current_time
        self._history.append(state)

        # Update hero memory from visible enemies
        for hero in state.visible_enemies:
            self._update_hero(hero, state.current_time)

        # Update hero memory from visible allies
        for hero in state.visible_allies:
            self._update_hero(hero, state.current_time)

        # Update missing durations for all tracked heroes
        for name, mem in self._hero_memory.items():
            if mem.last_seen_time > 0:
                mem.missing_duration = self._current_time - mem.last_seen_time

    def _update_hero(self, hero: HeroPosition, time: float) -> None:
        """Update memory for a single hero sighting."""
        name = hero.name
        if name not in self._hero_memory:
            self._hero_memory[name] = HeroMemory(name=name, team=hero.team)

        mem = self._hero_memory[name]
        mem.last_seen_time = time
        mem.last_position = (hero.x, hero.y)
        mem.last_lane = hero.lane
        mem.missing_duration = 0.0
        mem.trajectory.append((time, hero.x, hero.y))

        # Keep trajectory bounded
        if len(mem.trajectory) > 100:
            mem.trajectory = mem.trajectory[-50:]

    def get_enemy_missing(self) -> List[dict]:
        """Get all currently missing enemies with their missing duration.

        Returns:
            List of dicts: [{'name': str, 'missing_seconds': float, 'last_lane': str}]
        """
        missing = []
        for name, mem in self._hero_memory.items():
            if mem.team == Team.RED and mem.missing_duration > 0:
                missing.append({
                    "name": name,
                    "missing_seconds": mem.missing_duration,
                    "last_lane": mem.last_lane,
                    "last_position": mem.last_position,
                })
        # Sort by missing duration (longest first)
        missing.sort(key=lambda x: x["missing_seconds"], reverse=True)
        return missing

    def get_hero_memory(self, name: str) -> Optional[HeroMemory]:
        """Get memory for a specific hero."""
        return self._hero_memory.get(name)

    def get_hero_trajectory(
        self, name: str, last_n: int = 10
    ) -> list[tuple[float, float, float]]:
        """Get recent trajectory for a hero.

        Returns:
            List of (time, x, y) tuples, most recent last.
        """
        mem = self._hero_memory.get(name)
        if mem is None:
            return []
        return mem.trajectory[-last_n:]

    def get_jungler_missing_duration(self) -> float:
        """Get how long the enemy jungler has been missing.

        Returns 0 if jungler is visible or not tracked.
        """
        # Heuristic: jungler is the hero missing longest from any lane
        max_missing = 0.0
        for name, mem in self._hero_memory.items():
            if mem.team == Team.RED and mem.missing_duration > max_missing:
                max_missing = mem.missing_duration
        return max_missing

    def get_history(self, last_n: int = 5) -> list[GameState]:
        """Get the most recent N GameState snapshots."""
        return list(self._history)[-last_n:]

    def get_all_tracked_heroes(self) -> Dict[str, HeroMemory]:
        """Get all tracked hero memories."""
        return dict(self._hero_memory)

    def clear(self) -> None:
        """Reset all memory."""
        self._history.clear()
        self._hero_memory.clear()
        self._current_time = 0.0
