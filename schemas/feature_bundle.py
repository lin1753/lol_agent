"""Feature Bundle — unified container for all 6 Features."""

from __future__ import annotations

from pydantic import BaseModel

from schemas.economy import EconomyFeature
from schemas.hero import HeroFeature
from schemas.map import MapFeature
from schemas.objective import ObjectiveFeature
from schemas.skill import SkillFeature
from schemas.wave import WaveFeature


class FeatureBundle(BaseModel):
    """All Features extracted from a single frame.

    This is the primary output of FeatureEngine and the primary input
    to downstream engines (Context, Goal, Decision).
    """

    hero: HeroFeature = HeroFeature()
    economy: EconomyFeature = EconomyFeature()
    skill: SkillFeature = SkillFeature()
    wave: WaveFeature = WaveFeature()
    objective: ObjectiveFeature = ObjectiveFeature()
    map: MapFeature = MapFeature()
