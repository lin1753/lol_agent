# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LOL Agent Assistant — a real-time game understanding agent for League of Legends. Captures the live game screen, runs YOLO 29-class detection + PaddleOCR (YOLO-guided), OpenCV minimap analysis, maintains a temporal memory of game state, applies rule-based reasoning, and outputs tactical warnings via draggable overlay and voice.

**Not** a bot, RL player, or automated controller. It produces advice only.

Target hardware: RTX 4060 Laptop, single-developer project.

## Architecture

```
Screen/Video Capture → Full-frame YOLO (29 classes)
                            ↓
              ┌─────────────┼──────────────┐
              ↓             ↓              ↓
    game_time bbox    hero HP bars    skills/minions/towers
    → OCR read time   → ally/enemy    → game state enrichment
    KDA bbox             detection
    → OCR read KDA
    gold bbox
    → OCR read gold
              ↓             ↓              ↓
              └──────┬──────┘              │
                     ↓                     │
    Minimap Parser (OpenCV HSV) ←──────────┘
              ↓
         GameState
              ↓
    Temporal Memory (30s window)
              ↓
    State Understanding Engine (6 sub-engines)
      → phase / context / combat / lane / threat / objectives
              ↓
       Decision Engine (20 rules, alert + suggestion)
              ↓
    Overlay (draggable status panel) + Voice (Edge TTS)
```

Key design: **YOLO locates UI elements → OCR reads their content**. This makes the system layout-agnostic — works for live games, replays, and videos without hardcoded ROI positions. OCR results are cached across frames so timestamps persist.

### Core modules

| Directory | Responsibility |
|---|---|
| `capture/` | Screen capture (`mss`) + video file input (OpenCV), ROI manager |
| `perception/` | YOLO 29-class inference, OpenCV minimap parser, PaddleOCR (subprocess-isolated), detection summary |
| `parser/` | StateParser — YOLO/minimap detections → GameState |
| `models/` | GameState pydantic model |
| `memory/` | TemporalMemory — per-hero tracking, missing duration, trajectory |
| `reasoning/` | `StateEngine` (6 sub-engines) + `RuleEngine` (20 rules, alert+suggestion) |
| `overlay/` | PyQt5 draggable status panel with game state + color-coded warnings |
| `voice/` | Edge TTS (zh-CN-YunxiNeural) with async dedup, pyttsx3 fallback |
| `configs/` | ROI configs (`roi_config.json` for video, `roi_config_live.json` for live game) |

### 29-class YOLO model

Trained on 719 images (575/124 train/val split). Classes include: minimap, minimap_fov, KDA, game_time, hero HP bars (green/blue/red), HP bar UI elements, minions, cannons, towers, baron, herald, dragon, skills (Q/W/E/R/D/F), gold, player HP bar, player level.

Model: YOLOv8m at 1024px input → mAP50=87.1%, ~71 FPS.

### OCR subsystem

PaddleOCR 2.10.0 runs in a **subprocess** to avoid PyTorch CUDA conflicts. Communication via JSON over stdin/stdout. YOLO provides bounding boxes for game_time, KDA, gold, level — OCR reads only those regions with 4x upscale + adaptive thresholding.

## Commands

```bash
# Run with live game
python main.py --model models/center_29.pt

# Run with video
python main.py --model models/center_29.pt --video "path/to/video.mp4"

# Run without voice (debug)
python main.py --model models/center_29.pt --video "path/to/video.mp4" --no-voice

# Train YOLO
python scripts/train_yolo.py --data data/center_29_dataset/dataset.yaml --model yolov8m --epochs 100 --batch 4 --imgsz 1024

# Run tests
python -m pytest tests/ -v --ignore=tests/test_ocr.py

# OCR tests (must run separately to avoid torch/paddle conflict)
python -m pytest tests/test_ocr.py -v
```

Code formatter: Black.

### Environment notes

- PaddlePaddle 2.6.2 + PaddleOCR 2.10.0 + PyTorch 2.5.1 coexistence
- PaddleOCR runs in subprocess to avoid `_gpuDeviceProperties` CUDA type conflict
- GPU OCR requires `nvidia-cudnn-cu12==8.9.7.29` (PaddlePaddle needs cuDNN 8, PyTorch has cuDNN 9)
- NVIDIA DLL paths auto-added in `ocr_engine.py`

## Key Data Resources

Training data at `D:\Project\lol_yolo\data`:

| Path | Content |
|---|---|
| [images](../lol_yolo/data/images) | 719 labeled game screenshots |
| [label_xml](../lol_yolo/data/label_xml) | Pascal VOC XML annotations (48 classes) |
| [05_game_heroes_in_view_eval.json](../lol_yolo/data/05_game_heroes_in_view_eval.json) | Hero vision VQA (391 entries) |
| [06_game_minimap_heros_understanding_eval.json](../lol_yolo/data/06_game_minimap_heros_understanding_eval.json) | Minimap VQA (415 entries) |
| [hero_name.csv](../lol_yolo/data/hero_name.csv) | Hero name mappings (173 heroes) |
| [class_map.txt](../lol_yolo/data/class_map.txt) | Class ID to name (UTF-16, 48 classes) |

Generated datasets: `data/center_31_dataset/` (31-class, 575/124 split).

Design documents in `docs/` and project root:
- `LOL_Agent_DataSchema_V2.0.md` — V2.0 unified data schema
- `LOL_Agent_系统设计说明书_V2.0.md` — V2.0 system design
- `docs/v2_diff_analysis.md` — V2.0 vs V1 diff analysis
- `docs/optimization_v3.md` — HP bar combat optimization

## Language

Code, comments, and variable names should be in English. Design documents in Chinese.
