"""Objective Feature — neutral objective alive status."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ObjectiveFeature(BaseModel):
    """Map objective status from YOLO detections."""

    dragon_alive: bool = Field(default=False)
    grub_alive: bool = Field(default=False)
    herald_alive: bool = Field(default=False)
    baron_alive: bool = Field(default=False)
    elder_alive: bool = Field(default=False)
