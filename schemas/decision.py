"""Decision — candidate action with score and reason."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Decision(BaseModel):
    """A candidate action produced by DecisionEngineV2.

    Decisions are ranked by score (higher = more recommended).
    """

    action: str = Field(default="", description="Action identifier")
    score: float = Field(default=0.0, ge=0.0, le=100.0, description="Action score (0~100)")
    reason: str = Field(default="", description="Human-readable reason for this action")
