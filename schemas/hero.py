"""Hero Feature — visible hero counts and HP state."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HeroFeature(BaseModel):
    """Hero presence and HP features extracted from YOLO HP bar detections.

    HP values are percentages (0~100).
    """

    ally_count: int = Field(default=0, ge=0, description="Ally heroes visible on screen")
    enemy_count: int = Field(default=0, ge=0, description="Enemy heroes visible on screen")
    ally_hp_avg: float = Field(default=0.0, ge=0.0, description="Average ally HP bar area (proxy for HP)")
    enemy_hp_avg: float = Field(default=0.0, ge=0.0, description="Average enemy HP bar area (proxy for HP)")
    ally_hp_total: float = Field(default=0.0, ge=0.0, description="Sum of ally HP percentages")
    enemy_hp_total: float = Field(default=0.0, ge=0.0, description="Sum of enemy HP percentages")
    visible_allies: int = Field(default=0, ge=0, description="Allies in center viewport")
    visible_enemies: int = Field(default=0, ge=0, description="Enemies in center viewport")

    @property
    def hp_ratio(self) -> float:
        """HP advantage ratio: -1.0 (all enemy) to +1.0 (all ally), 0 = equal."""
        total = self.ally_hp_total + self.enemy_hp_total
        if total == 0:
            return 0.0
        return (self.ally_hp_total - self.enemy_hp_total) / total
