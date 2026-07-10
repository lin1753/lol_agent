"""Centralized configuration for LOL Agent."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure logging for the application."""
    logger = logging.getLogger("lol_agent")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger


@dataclass
class AgentConfig:
    """All configurable parameters in one place.

    Priority: CLI args > env vars > defaults.
    Use AgentConfig.from_args(argparse_namespace) to build from CLI.
    """

    # Pipeline
    fps_target: float = 5.0
    memory_window: int = 30

    # OCR
    ocr_lang: str = "ch"
    ocr_interval: int = 60        # frames between OCR calls
    status_interval: int = 30     # frames between console status prints

    # Model paths (None = disabled)
    yolo_model: str | None = None
    llm_model: str | None = None  # fallback: LOL_LLM_MODEL_PATH env

    # Overlay position
    overlay_x: int = 1500
    overlay_y: int = 50
    overlay_width: int = 320

    # FeatureEngine thresholds
    skill_confidence: float = 0.7
    level_max: int = 18

    # Objective timing — 2025/2026 season (seconds)
    dragon_first_spawn: int = 300    # 5:00
    dragon_respawn: int = 300        # 5 min
    baron_first_spawn: int = 1500    # 25:00
    baron_respawn: int = 360         # 6 min
    herald_first_spawn: int = 480    # 8:00
    herald_despawn: int = 1170       # 19:30

    @classmethod
    def from_args(cls, args) -> AgentConfig:
        """Build config from argparse namespace with env var fallbacks."""
        cfg = cls()
        if getattr(args, "fps", None):
            cfg.fps_target = args.fps
        if getattr(args, "model", None):
            cfg.yolo_model = args.model
        if getattr(args, "llm_model", None):
            cfg.llm_model = args.llm_model
        elif not cfg.llm_model:
            cfg.llm_model = os.environ.get("LOL_LLM_MODEL_PATH")
        return cfg
