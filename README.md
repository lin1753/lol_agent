# LOL Agent Assistant

实时游戏理解 Agent — 基于 YOLO + OCR + 战术引擎的英雄联盟助手。

> **不是**外挂、自动操作或 AI 代打。只产出战术建议，不操作游戏。

---

## 设计哲学

本项目的核心不是"检测到了什么"，而是**是否维护了游戏世界状态**。

| 普通 CV | Agent |
|---|---|
| 检测到敌方英雄 | 敌方打野已 20 秒未出现 |
| 识别出血条 | 我方下路血量劣势，可能被越塔 |

因此，系统的灵魂是 **GameState + Temporal Memory + Reasoning Engine**，而非单纯的 YOLO 训练。

---

## 系统架构

### V1 Pipeline（规则驱动）

```
Screen Capture → ROI Crop → YOLO 32-class Detection
    → Detection Summary → OCR (game_time, KDA, gold, level)
    → Minimap Parser (OpenCV HSV)
    → StateParser → GameState
    → TemporalMemory (30s rolling window)
    → StateEngine (6 sub-engines) → RuleEngine (20 rules)
    → Overlay (PyQt5) + Voice (Edge TTS)
```

### V2 Pipeline（目标驱动，`--v2`）

```
Screen Capture → ROI Crop → YOLO + OCR
    → FeatureEngine → FeatureBundle (6 Features)
    → MemoryV2 (Hero + Objective + Fight)
    → ContextEngine (7 contexts) → GameStateV2 (5 dimensions)
    → GoalEngine (9 goals) → DecisionEngineV2 (scored actions)
    → [Optional] LlmEngine (Qwen3-8B) → Natural language advice
    → Overlay + Voice
```

**核心数据流：**
```
YOLO Detector → FeatureEngine → FeatureBundle → MemoryEngine
→ GameState → GoalEngine → DecisionEngine → [LLM] → Overlay + TTS
```

---

## 快速开始

### 环境要求

| 依赖 | 版本 | 说明 |
|---|---|---|
| Python | 3.11+ | 推荐 3.11 |
| PyTorch | 2.6+ (CUDA) | GPU 推理 |
| PaddlePaddle | 2.6.2 | OCR 引擎 |
| PaddleOCR | 2.10.0 | 子进程隔离运行 |
| ultralytics | 8.x | YOLOv8 推理 |
| PyQt5 | 5.15 | 悬浮窗 UI |
| mss | 10.x | 屏幕捕获 |

### 安装

```bash
# 创建虚拟环境（推荐 uv）
uv venv --python 3.11 .venv
.venv\Scripts\activate

# 安装 PyTorch CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# 安装项目依赖
pip install opencv-python ultralytics mss pydantic "pyqt5<6.0" pyttsx3 paddleocr paddlepaddle-gpu pandas tqdm pytest

# 降级 albumentations（避免导入 torch 冲突）
pip install "albumentations<2.0"
```

### 运行

```bash
# 实时游戏（自动检测 LOL 窗口）
python main.py --model runs/detect/runs/train/lol_yolo/weights/best.pt

# 视频文件测试
python main.py --model runs/detect/runs/train/lol_yolo/weights/best.pt --video path/to/video.mp4

# V2 流水线 + 调试信息
python main.py --v2 --debug --model runs/detect/runs/train/lol_yolo/weights/best.pt --video path/to/video.mp4

# 指定窗口捕获（如 B 站直播）
python main.py --model runs/detect/runs/train/lol_yolo/weights/best.pt --window "bilibili"

# 指定显示器
python main.py --model runs/detect/runs/train/lol_yolo/weights/best.pt --monitor 1
```

### CLI 参数

| 参数 | 说明 |
|---|---|
| `--model` | YOLO 权重路径 |
| `--video` | 视频文件路径（测试用） |
| `--v2` | 启用 V2 目标驱动流水线 |
| `--llm` | 启用 Qwen3-8B LLM 建议（需 `--v2`，需 6GB+ 显存） |
| `--debug` | 显示 YOLO/OCR/Feature 调试信息 |
| `--window` | 指定窗口标题捕获 |
| `--monitor` | 显示器编号或 `auto` |
| `--no-overlay` | 禁用悬浮窗 |
| `--no-voice` | 禁用语音 |
| `--fps` | 目标帧率（默认 5） |
| `--cpu` | 强制 CPU 模式 |

---

## 项目结构

```
lol_agent/
├── main.py                        # 主入口，LolAgent 编排所有模块
│
├── capture/                       # 屏幕捕获
│   ├── screen_capture.py          # mss 截图 + Win32 窗口检测
│   └── roi_manager.py             # ROI 裁剪（minimap/center/topbar/hud）
│
├── perception/                    # 感知层
│   ├── yolo_infer.py              # 多模型 YOLO 推理引擎
│   ├── detection_summary.py       # 检测结果分类汇总
│   ├── minimap_parser.py          # OpenCV HSV 颜色分割 + Hough 圆检测
│   └── ocr_engine.py              # PaddleOCR 子进程隔离（JSON over stdin/stdout）
│
├── parser/                        # 状态解析
│   └── state_parser.py            # YOLO/OCR → GameState（V1）
│
├── models/                        # 核心数据模型
│   └── game_state.py              # GameState Pydantic model（V1）
│
├── schemas/                       # V2 统一数据规范（11 个 Pydantic Schema）
│   ├── hero.py                    # HeroFeature
│   ├── economy.py                 # EconomyFeature
│   ├── skill.py                   # SkillFeature
│   ├── wave.py                    # WaveFeature
│   ├── objective.py               # ObjectiveFeature
│   ├── map.py                     # MapFeature
│   ├── feature_bundle.py          # FeatureBundle（6 合 1）
│   ├── state.py                   # GameStateV2（5 维状态）
│   ├── goal.py                    # Goal（9 种战略目标）
│   └── decision.py                # Decision（候选动作 + 评分）
│
├── memory/                        # 记忆系统
│   ├── temporal_memory.py         # V1 滚动窗口时序记忆
│   ├── hero_memory.py             # V2 英雄追踪（proximity matching）
│   ├── objective_memory.py        # V2 中立资源计时
│   └── fight_memory.py            # V2 团战/死亡事件记录
│
├── reasoning/                     # 推理引擎
│   ├── state_engine.py            # V1 六子引擎（phase/activity/combat/lane/threat/timer）
│   ├── rule_engine.py             # V1 20 条规则（10 alert + 10 suggestion）
│   ├── feature_engine.py          # V2 特征提取（Detection → FeatureBundle）
│   ├── context_engine.py          # V2 场景识别（7 种上下文）
│   ├── goal_engine.py             # V2 目标决策（9 种目标 + 置信度）
│   ├── decision_engine_v2.py      # V2 目标驱动决策（规则映射 + 评分去重）
│   └── llm_engine.py              # Qwen3-8B 本地推理（4-bit 量化）
│
├── overlay/                       # UI
│   └── overlay_ui.py              # PyQt5 可拖拽透明悬浮窗（V1 + V2）
│
├── voice/                         # 语音
│   └── tts_engine.py              # Edge TTS (zh-CN-YunxiNeural) + pyttsx3 fallback
│
├── configs/                       # ROI 配置
│   ├── roi_config.json            # B 站回放/视频布局（1920x1080，红方）
│   └── roi_config_live.json       # 实时游戏布局（1920x1080，蓝方）
│
├── scripts/                       # 工具脚本
│   ├── train_yolo.py              # YOLO 训练
│   ├── convert_voc_to_yolo.py     # VOC → YOLO 格式转换
│   └── build_center_dataset.py    # 构建 31-class 数据集
│
├── tests/                         # 测试套件（245 tests）
└── data/                          # 训练数据 + 调试图片
```

---

## 核心设计

### 感知层：YOLO 定位 + OCR 读取

设计关键：**YOLO 负责定位 UI 元素，OCR 负责读取内容**。这使系统与布局无关——适用于直播、回放、录屏。

| YOLO 检测类 | 数量 | 说明 |
|---|---|---|
| UI 信息 | 5 | game_time, kda, gold, player_level, player_hp_bar |
| 英雄 HP | 6 | green/blue/red_hp_hero + green/blue/red_hp_bar |
| 兵线 | 4 | red/blue_minion, red/blue_cannon |
| 建筑 | 2 | blue/red_tower |
| 中立资源 | 4 | dragon, herald, void_grub, baron |
| 技能 | 6 | q/w/e/r/d/f_skill |
| 小地图 | 2 | minimap, minimap_fov |
| 其他 | 3 | ally_hero_icon, enemy_hero_icon, equipment |

- **模型**: YOLOv8m, 32 classes, 1024px input
- **训练数据**: 719 张游戏截图（575/124 train/val split）
- **mAP50**: ~87%
- **权重**: `runs/detect/runs/train/lol_yolo/weights/best.pt`

### V1 状态理解（6 子引擎）

| 子引擎 | 输出 | 说明 |
|---|---|---|
| Phase | early / mid / late | 0-14 / 14-25 / 25+ 分钟 |
| Activity | laning / roaming / skirmish / teamfight / objective / reset | 当前活动 |
| Combat | advantage / even / disadvantage | HP 条面积比 |
| Lane | neutral / pushing / being_pushed | 兵线态势 |
| Threat | low / medium / high | 综合威胁度 |
| Timers | dragon / baron / herald 倒计时 | 中立资源计时 |

### V2 策略引擎

#### Context Engine（7 种场景）

| 场景 | 触发条件 |
|---|---|
| retreat | 血量极低 / 被包围无闪现 |
| collapse | 敌方推线 + 人数劣势 |
| contest | 目标即将刷新 + 双方争夺 |
| siege | 兵线推进 + 人数优势 |
| defense | 敌方兵线推进 |
| pressure | 兵线优势 + 敌方消失 |
| safe_farm | 默认安全发育 |

#### Goal Engine（9 种战略目标）

`contest_dragon` / `contest_baron` / `contest_herald` / `push_tower` / `defend_tower` / `split_push` / `group` / `retreat` / `farm`

#### 等级策略

| 等级范围 | 行为倾向 |
|---|---|
| < 6 (pre_6) | 优先发育，避免团战 |
| 6-10 (spike_6) | 大招优势期，寻找机会 |
| 11+ | 正常决策 |

#### 中立资源计时（2025/2026 赛季）

| 资源 | 位置 | 首次刷新 | 刷新间隔 |
|---|---|---|---|
| 元素亚龙 | 下河道 | 5:00 | 5:00 |
| 远古巨龙 | 下河道 | 龙魂后 | 10:00 |
| 巢虫 | 上河道 | 5:00 | 一次性 |
| 先锋 | 上河道 | 8:00 | 一次性（19:30 消失） |
| 男爵 | 上河道 | 25:00 | 6:00 |

### V2 数据 Schema（11 个 Pydantic 对象）

整个系统的统一数据协议，模块间禁止传递裸 dict：

```
FeatureLayer:   HeroFeature / EconomyFeature / SkillFeature
                WaveFeature / ObjectiveFeature / MapFeature
                        ↓
                FeatureBundle（6 合 1 容器）
                        ↓
MemoryLayer:    HeroMemoryV2 / ObjectiveMemory / FightMemory
                        ↓
StateLayer:     GameStateV2（phase / activity / context / combat / threat）
                        ↓
GoalLayer:      Goal（goal_type + confidence）
                        ↓
DecisionLayer:  Decision（action + score + reason）
```

### 记忆系统

| 记忆类型 | 功能 |
|---|---|
| TemporalMemory (V1) | 30 帧滚动窗口，per-hero last_seen/trajectory |
| HeroMemoryV2 | Proximity matching 追踪英雄，计算失踪时长 |
| ObjectiveMemory | 龙/先锋/男爵击杀/刷新计时 |
| FightMemory | 近期团战胜率、死亡事件 |

### OCR 子进程隔离

PaddleOCR 运行在独立 Python 子进程中，通过 JSON over stdin/stdout 通信。原因：PaddlePaddle 与 PyTorch 的 CUDA 绑定在 Windows 下存在 `_gpuDeviceProperties` 类型冲突。OCR 默认使用 CPU 模式。

---

## 测试

```bash
# 全量测试（排除 OCR，避免 CUDA 冲突）
python -m pytest tests/ --ignore=tests/test_ocr.py -v

# OCR 单独测试
python -m pytest tests/test_ocr.py -v

# 单模块测试
python -m pytest tests/test_feature_engine.py -v
python -m pytest tests/test_decision_engine_v2.py -v
python -m pytest tests/test_schemas.py -v
```

---

## 训练

```bash
# 转换 VOC 标注 → YOLO 格式
python scripts/convert_voc_to_yolo.py --data-dir D:\Project\lol_yolo\data

# 构建 31-class 数据集
python scripts/build_center_dataset.py --data-dir D:\Project\lol_yolo\data

# 训练 YOLO
python scripts/train_yolo.py --data data/center_31_dataset/dataset.yaml --model yolov8m --epochs 100 --batch 4 --imgsz 1024
```

---

## 开发路线

| 阶段 | 内容 | 状态 |
|---|---|---|
| V1.0 | Capture → YOLO → OCR → GameState → TemporalMemory → RuleEngine → Overlay/TTS | ✅ 完成 |
| V1.5 | 双数据源（YOLO + OpenCV minimap）、YOLO 引导 OCR、战斗状态 | ✅ 完成 |
| V2.0 | Schemas → FeatureEngine → Context/Goal/Decision → LLM → MemoryV2 | ✅ 完成 |
| V2.5 | 等级策略、目标计时修复、debug 模式 | ✅ 完成 |
| V3.0 | Transformer 时序预测（需大量对局数据） | 🔮 远期 |

---

## 设计原则

1. **统一字段命名** — 禁止 `enemy_num`/`enemy_cnt` 混用，统一 `enemy_count`
2. **Schema 驱动** — 所有模块输入输出基于 Pydantic BaseModel，禁止裸 dict 传递
3. **JSON 交换格式** — 模块间通信使用 JSON 序列化
4. **LLM 只接收结构化输入** — 禁止 YOLO 原始框直接送入 LLM

---

## License

MIT
