"""Decision — candidate action with score and reason."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ActionType = Literal[
    "contest_dragon", "contest_baron", "contest_herald",
    "push_tower", "defend_tower", "split_push",
    "group", "retreat", "farm",
    "prepare_vision", "push_lane_pressure", "sneak_baron",
    "recall", "play_safe", "prepare_objective",
]


class Decision(BaseModel):
    """A candidate action produced by DecisionEngineV2.

    Decisions are ranked by score (higher = more recommended).
    """

    action: ActionType = Field(default="farm", description="Action identifier")
    score: float = Field(default=0.0, ge=0.0, le=100.0, description="Action score (0~100)")
    reason: str = Field(default="", description="Human-readable reason for this action")
