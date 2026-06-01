"""Map Feature — enemy distribution across lanes from minimap."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MapFeature(BaseModel):
    """Map awareness features from minimap detections."""

    enemy_top: int = Field(default=0, ge=0, description="Enemies in top lane area")
    enemy_mid: int = Field(default=0, ge=0, description="Enemies in mid lane area")
    enemy_bot: int = Field(default=0, ge=0, description="Enemies in bot lane area")
    enemy_missing: int = Field(default=0, ge=0, description="Enemy heroes not seen on minimap")

    @property
    def enemy_visible_total(self) -> int:
        return self.enemy_top + self.enemy_mid + self.enemy_bot
