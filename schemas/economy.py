"""Economy Feature — player gold, level, KDA, items."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EconomyFeature(BaseModel):
    """Player economy features extracted from OCR results."""

    player_level: int = Field(default=1, ge=1, le=18)
    player_gold: int = Field(default=0, ge=0)
    item_count: int = Field(default=0, ge=0, le=6)
    kills: int = Field(default=0, ge=0)
    deaths: int = Field(default=0, ge=0)
    assists: int = Field(default=0, ge=0)

    @property
    def has_ult(self) -> bool:
        """True if player is level 6+ (ult unlocked)."""
        return self.player_level >= 6

    @property
    def level_spike(self) -> str:
        """Current power spike tier: pre_6 / spike_6 / spike_11 / spike_16 / max."""
        if self.player_level < 6:
            return "pre_6"
        elif self.player_level < 11:
            return "spike_6"
        elif self.player_level < 16:
            return "spike_11"
        else:
            return "spike_16"

    @property
    def is_pre_6(self) -> bool:
        """True if player hasn't reached level 6 yet."""
        return self.player_level < 6
