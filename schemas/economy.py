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
