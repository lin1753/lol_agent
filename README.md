# LOL Agent Assistant

实时游戏理解 Agent — 基于 YOLO + OCR + 战术引擎的英雄联盟助手。

**不是**外挂、自动操作或 AI 代打。只产出建议，不操作游戏。

## 架构

```
Screen/Video Capture → YOLO (32-class) → Detection Summary
    ↓
Feature Engine → FeatureBundle (6 Features)
    ↓
Memory V2 (Hero/Objective/Fight) → MemoryState
    ↓
Context Engine → GameState V2 (5 dimensions)
    ↓
Goal Engine (9 goals) → Decision Engine V2 (scored actions)
    ↓
Qwen3-8B LLM (optional) → Natural language advice
    ↓
Overlay (PyQt5) + Voice (Edge TTS)
```

### V1 Pipeline
```
YOLO → StateParser → GameState → TemporalMemory → RuleEngine (20 rules) → Overlay
```

### V2 Pipeline
```
YOLO → FeatureEngine → ContextEngine → GoalEngine → DecisionEngineV2 → Overlay
```

## Quick Start

```bash
# 安装依赖
pip install -r requirements.txt

# V1 模式（原有流程）
python main.py --model runs/detect/runs/train/lol_yolo/weights/best.pt --video path/to/video.mp4

# V2 模式（新架构）
python main.py --v2 --model runs/detect/runs/train/lol_yolo/weights/best.pt --video path/to/video.mp4

# V2 + 调试模式
python main.py --v2 --debug --model runs/detect/runs/train/lol_yolo/weights/best.pt --video path/to/video.mp4

# V2 + LLM 建议
python main.py --v2 --llm --model runs/detect/runs/train/lol_yolo/weights/best.pt

# 实时游戏
python main.py --v2 --model runs/detect/runs/train/lol_yolo/weights/best.pt
```

### CLI 参数

| 参数 | 说明 |
|---|---|
| `--model` | YOLO 权重路径 |
| `--video` | 视频文件路径（测试用） |
| `--v2` | 启用 V2 pipeline |
| `--llm` | 启用 Qwen3-8B LLM 建议（需 `--v2`） |
| `--debug` | 显示 YOLO/OCR/Feature 调试信息 |
| `--no-overlay` | 禁用悬浮窗 |
| `--no-voice` | 禁用语音 |
| `--fps` | 目标帧率（默认 5） |
| `--cpu` | 强制 CPU 模式 |

## 项目结构

```
lol_agent/
├── main.py                    # 主入口
├── schemas/                   # V2 Pydantic 数据模型
│   ├── hero.py               # HeroFeature（HP/人数）
│   ├── economy.py            # EconomyFeature（KDA/金币/等级）
│   ├── skill.py              # SkillFeature（技能就绪）
│   ├── wave.py               # WaveFeature（兵线）
│   ├── objective.py          # ObjectiveFeature（中立资源）
│   ├── map.py                # MapFeature（小地图）
│   ├── feature_bundle.py     # FeatureBundle（6合1）
│   ├── state.py              # GameStateV2（5维状态）
│   ├── goal.py               # Goal（9种战略目标）
│   └── decision.py           # Decision（候选动作）
├── reasoning/                 # 推理引擎
│   ├── feature_engine.py     # V2 特征提取
│   ├── context_engine.py     # 场景识别（7种）
│   ├── goal_engine.py        # 目标决策（9种）
│   ├── decision_engine_v2.py # 候选动作排序
│   ├── llm_engine.py         # Qwen3-8B 推理
│   ├── state_engine.py       # V1 状态理解
│   └── rule_engine.py        # V1 规则引擎
├── memory/                    # 记忆系统
│   ├── temporal_memory.py    # V1 时序记忆
│   ├── hero_memory.py        # V2 英雄追踪
│   ├── objective_memory.py   # V2 目标计时
│   └── fight_memory.py       # V2 团战记录
├── perception/                # 感知层
│   ├── yolo_infer.py         # YOLO 推理
│   ├── detection_summary.py  # 检测汇总
│   ├── minimap_parser.py     # 小地图解析（OpenCV）
│   └── ocr_engine.py         # PaddleOCR（子进程隔离）
├── overlay/                   # UI
│   └── overlay_ui.py         # PyQt5 悬浮窗（V1 + V2）
├── voice/                     # 语音
│   └── tts_engine.py         # Edge TTS
├── capture/                   # 捕获
│   ├── screen_capture.py     # 屏幕截图
│   └── roi_manager.py        # ROI 管理
├── configs/                   # 配置
├── tests/                     # 测试
├── scripts/                   # 训练脚本
└── data/                      # 数据集
```

## YOLO 模型

- **模型**: YOLOv12m, 32 classes, 1024px input
- **推理速度**: ~12ms/帧（~83 FPS）
- **训练数据**: 719 张游戏截图
- **权重**: `runs/detect/runs/train/lol_yolo/weights/best.pt`

### 32-class 识别目标

| 类别 | 内容 |
|---|---|
| UI | game_time, kda, gold, player_level, player_hp_bar |
| 英雄 | green/blue/red_hp_hero, green/blue/red_hp_bar |
| 兵线 | red/blue_minion, red/blue_cannon |
| 建筑 | blue/red_tower |
| 资源 | dragon, herald, void_grub, baron |
| 技能 | q/w/e/r/d/f_skill |
| 小地图 | minimap, minimap_fov |

## V2 策略引擎

### Context Engine（7 种场景）

| 场景 | 条件 |
|---|---|
| retreat | 血量极低 / 被包围无闪现 |
| collapse | 敌方推线 + 人数劣势 |
| contest | 客观即将刷新 + 双方争夺 |
| siege | 兵线推进 + 人数优势 |
| defense | 敌方兵线推进 |
| pressure | 兵线优势 + 敌方消失 |
| safe_farm | 默认 |

### Goal Engine（9 种目标）

contest_dragon / contest_baron / contest_herald / push_tower / defend_tower / split_push / group / retreat / farm

### Decision Engine

- 每个 Goal 映射多条候选规则
- 动作去重 + 评分排序
- 理由包含具体数字（人数/HP/技能/等级）

### 等级策略

| 等级 | 行为 |
|---|---|
| pre_6 (<6) | 优先发育，避免团战 |
| spike_6 (6-10) | 大招优势，寻找机会 |
| spike_11+ | 正常决策 |

### 中立资源计时（2025/2026 赛季）

| 资源 | 龙坑 | 首次刷新 | 刷新间隔 |
|---|---|---|---|
| 元素亚龙 | 下河道 | 5:00 | 5:00 |
| 远古巨龙 | 下河道 | Soul 后 | 10:00 |
| 巢虫 | 上河道 | 5:00 | 一次性 |
| 先锋 | 上河道 | 8:00 | 一次性（19:30消失） |
| 男爵 | 上河道 | 25:00 | 6:00 |

## 测试

```bash
# 全量测试（排除 OCR）
python -m pytest tests/ --ignore=tests/test_ocr.py -v

# 单模块测试
python -m pytest tests/test_feature_engine.py -v
python -m pytest tests/test_decision_engine_v2.py -v
```

## 环境

- Python 3.10+
- PyTorch 2.5+ (CUDA 12.1)
- PaddleOCR 2.10.0（子进程隔离，避免 CUDA 冲突）
- PyQt5（overlay）
- Edge TTS（语音）

## License

MIT
