"""GameState V2 — simplified 5-dimensional game state."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GameStateV2(BaseModel):
    """Simplified game state with 5 understanding dimensions.

    Replaces V1 GameState's mixed fields. Features live in FeatureBundle;
    this only holds derived understanding.
    """

    game_time: float = Field(default=0.0, ge=0.0, description="Game time in seconds")

    phase: Literal["early", "mid", "late"] = Field(
        default="early",
        description="Game phase: early / mid / late",
    )
    activity: Literal["laning", "roaming", "skirmish", "teamfight", "objective", "reset"] = Field(
        default="laning",
        description="Current activity",
    )
    context: Literal["safe_farm", "pressure", "siege", "defense", "contest", "collapse", "retreat"] = Field(
        default="safe_farm",
        description="Situation context",
    )
    combat: Literal["advantage", "even", "disadvantage"] = Field(
        default="even",
        description="Combat advantage",
    )
    threat: Literal["low", "medium", "high"] = Field(
        default="low",
        description="Threat level",
    )

    # Objective timers
    dragon_spawn_in: float = Field(default=-1.0, description="Seconds until dragon spawns, -1 = unknown")
    baron_spawn_in: float = Field(default=-1.0, description="Seconds until baron spawns, -1 = unknown")
    herald_spawn_in: float = Field(default=-1.0, description="Seconds until herald spawns, -1 = unknown")
