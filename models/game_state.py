"""GameState — the central data structure for the LOL Agent system.

This is the core abstraction that transforms raw YOLO detections and OCR
results into a structured game world state. All downstream modules
(TemporalMemory, RuleEngine, Overlay) operate on GameState objects.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Team(str, Enum):
    """Team side."""

    BLUE = "blue"
    RED = "red"


class HeroPosition(BaseModel):
    """A hero's position on the map."""

    name: str
    team: Team
    x: float
    y: float
    lane: Optional[str] = None  # "top", "mid", "bot", "jungle", None


class ObjectiveStatus(BaseModel):
    """Status of a map objective."""

    alive: bool = True
    last_killed_time: Optional[float] = None
    respawn_time: Optional[float] = None


class GameState(BaseModel):
    """Complete game state at a single point in time.

    This is what the State Parser produces from YOLO+OCR output,
    and what TemporalMemory and RuleEngine consume.
    """

    # --- Timing ---
    current_time: float = Field(default=0.0, description="Game time in seconds")

    # --- Visible units ---
    visible_enemies: list[HeroPosition] = Field(default_factory=list)
    visible_allies: list[HeroPosition] = Field(default_factory=list)

    # --- Minimap positions ---
    minimap_enemy_positions: dict[str, tuple[float, float]] = Field(
        default_factory=dict,
        description="Enemy hero name -> (x, y) on minimap",
    )
    minimap_ally_positions: dict[str, tuple[float, float]] = Field(
        default_factory=dict,
        description="Ally hero name -> (x, y) on minimap",
    )

    # --- Missing heroes ---
    enemy_missing: list[str] = Field(
        default_factory=list,
        description="Enemy heroes not seen recently",
    )

    # --- Objectives ---
    dragon: ObjectiveStatus = Field(default_factory=ObjectiveStatus)
    herald: ObjectiveStatus = Field(default_factory=ObjectiveStatus)
    baron: ObjectiveStatus = Field(default_factory=ObjectiveStatus)

    # --- Player stats ---
    player_hp: float = Field(default=100.0, ge=0, le=100)
    player_mana: float = Field(default=100.0, ge=0, le=100)
    current_gold: int = Field(default=0, ge=0)
    player_level: int = Field(default=1, ge=1, le=18)

    # --- KDA ---
    kills: int = Field(default=0, ge=0)
    deaths: int = Field(default=0, ge=0)
    assists: int = Field(default=0, ge=0)

    # --- Derived / Inferred ---
    danger_lane: Optional[str] = Field(
        default=None,
        description="Most dangerous lane: 'top', 'mid', 'bot'",
    )
    teamfight_probability: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Probability of imminent teamfight (0-1)",
    )

    # --- Towers ---
    blue_towers_alive: int = Field(default=11, ge=0, le=11)
    red_towers_alive: int = Field(default=11, ge=0, le=11)

    # --- Minions (from YOLO 29-class) ---
    red_minion_count: int = Field(default=0, ge=0)
    blue_minion_count: int = Field(default=0, ge=0)
    red_cannon_count: int = Field(default=0, ge=0)
    blue_cannon_count: int = Field(default=0, ge=0)

    # --- State Understanding Engine output ---
    game_phase: str = Field(
        default="early_game",
        description="early_game (0-14min), mid_game (14-25min), late_game (25min+)",
    )
    context: str = Field(
        default="laning",
        description="laning, split_push, skirmish, teamfight, dragon_fight, baron_fight",
    )
    combat_state: str = Field(
        default="even",
        description="advantage, even, disadvantage",
    )
    combat_score: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="-1.0 (disadvantage) to +1.0 (advantage)",
    )
    lane_state: str = Field(
        default="neutral",
        description="pushing, being_pushed, neutral",
    )
    threat_level: str = Field(
        default="low",
        description="low, medium, high",
    )

    # --- Objective timers (seconds until next spawn, -1 = unknown) ---
    dragon_spawn_in: float = Field(default=-1, description="Seconds until dragon spawns")
    baron_spawn_in: float = Field(default=-1, description="Seconds until baron spawns")
    herald_spawn_in: float = Field(default=-1, description="Seconds until herald spawns")

    @property
    def enemy_count_visible(self) -> int:
        return len(self.visible_enemies)

    @property
    def ally_count_visible(self) -> int:
        return len(self.visible_allies)

    @property
    def missing_enemy_count(self) -> int:
        return len(self.enemy_missing)

    def get_hero_on_minimap(self, name: str) -> Optional[tuple[float, float]]:
        """Get a hero's position on minimap (checks both teams)."""
        return self.minimap_enemy_positions.get(
            name
        ) or self.minimap_ally_positions.get(name)
