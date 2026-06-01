"""Goal — strategic objective with confidence."""

from __future__ import annotations

from pydantic import BaseModel, Field


# 9 goal types as defined in LOL_Agent_DataSchema_V2.0.md
GOAL_TYPES = [
    "contest_dragon",
    "contest_baron",
    "contest_herald",
    "push_tower",
    "defend_tower",
    "split_push",
    "group",
    "retreat",
    "reset",
]


class Goal(BaseModel):
    """The current strategic goal determined by GoalEngine."""

    goal_type: str = Field(
        default="reset",
        description="Strategic goal type (one of GOAL_TYPES)",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this goal (0~1)",
    )
