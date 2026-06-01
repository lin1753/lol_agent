"""Skill Feature — ability and summoner spell readiness."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillFeature(BaseModel):
    """Skill availability detected by YOLO skill class detections."""

    q_ready: bool = Field(default=False)
    w_ready: bool = Field(default=False)
    e_ready: bool = Field(default=False)
    r_ready: bool = Field(default=False)
    d_ready: bool = Field(default=False)
    f_ready: bool = Field(default=False)

    @property
    def ult_ready(self) -> bool:
        return self.r_ready

    @property
    def flash_ready(self) -> bool:
        return self.d_ready or self.f_ready

    @property
    def combat_ready(self) -> bool:
        """True if at least QWER are available."""
        return self.q_ready and self.w_ready and self.e_ready and self.r_ready
