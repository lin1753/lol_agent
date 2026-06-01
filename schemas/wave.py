"""Wave Feature — minion and cannon counts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WaveFeature(BaseModel):
    """Minion wave features extracted from YOLO detections."""

    ally_minions: int = Field(default=0, ge=0, description="Blue side minions visible")
    enemy_minions: int = Field(default=0, ge=0, description="Red side minions visible")
    ally_cannons: int = Field(default=0, ge=0, description="Blue side cannons visible")
    enemy_cannons: int = Field(default=0, ge=0, description="Red side cannons visible")

    @property
    def wave_strength(self) -> float:
        """Ally wave strength relative to enemy (-1 to +1)."""
        ally = self.ally_minions + self.ally_cannons * 2
        enemy = self.enemy_minions + self.enemy_cannons * 2
        total = ally + enemy
        if total == 0:
            return 0.0
        return (ally - enemy) / total

    @property
    def lane_pressure(self) -> str:
        """Lane pressure level: low / medium / high."""
        ws = abs(self.wave_strength)
        if ws > 0.5:
            return "high"
        elif ws > 0.2:
            return "medium"
        return "low"
