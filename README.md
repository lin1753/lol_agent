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

---

## 系统架构

```
Screen Capture → ROI Crop → YOLO 32-class Detection (GPU)
    + OCR (PaddleOCR subprocess, base64 pipe)
    + Minimap Parser (OpenCV HSV)
    → ThreadPool 并行: YOLO ∥ OCR ∥ Minimap
    → FeatureEngine → FeatureBundle (6 Features)
    → ObjectiveMemory + FightMemory
    → ContextEngine (7 contexts) → GameStateV2 (5 dimensions)
    → GoalEngine (9 goals) → DecisionEngineV2 (scored actions)
    → [Optional] LlmEngine (Qwen3-8B) → Natural language advice
    → Overlay (PyQt5) + Voice (Edge TTS)
```

**核心数据流：**
```
YOLO Detector → FeatureEngine → FeatureBundle
→ ContextEngine → GoalEngine → DecisionEngine → [LLM] → Overlay + TTS
```

---

## 快速开始

### 环境要求

| 依赖 | 版本 | 说明 |
|---|---|---|
| Python | 3.11+ | 推荐 3.11 |
| PyTorch | 2.0+ (CUDA) | GPU 推理 |
| PaddleOCR | 2.7+ | OCR 引擎（子进程隔离） |
| ultralytics | 8.x | YOLOv8 推理 |
| PyQt5 | 5.15+ | 悬浮窗 UI |
| pydantic | 2.0+ | 数据 Schema |

### 安装

```bash
# 创建虚拟环境（推荐 uv）
uv venv --python 3.11 .venv
.venv\Scripts\activate

# 安装 PyTorch CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# 安装项目依赖（已锁定大版本）
pip install -r requirements.txt
```

### 运行

```bash
# 实时游戏（自动检测 LOL 窗口）
python main.py --model runs/detect/runs/train/lol_yolo/weights/best.pt

# 视频文件测试 + 调试信息
python main.py --debug --model best.pt --video path/to/video.mp4

# 启用 LLM 建议
python main.py --llm --llm-model /path/to/Qwen3-8B --model best.pt

# 指定窗口捕获（如 B 站直播）
python main.py --model best.pt --window "bilibili"
```

### CLI 参数

| 参数 | 说明 |
|---|---|
| `--model` | YOLO 权重路径 |
| `--video` | 视频文件路径（测试用） |
| `--llm` | 启用 LLM 建议（需 `--llm-model`，需 6GB+ 显存） |
| `--llm-model` | LLM 模型路径（或设置 `LOL_LLM_MODEL_PATH` 环境变量） |
| `--debug` | 显示 YOLO/OCR/Feature 调试信息 + profiling 耗时 |
| `--window` | 指定窗口标题捕获 |
| `--monitor` | 显示器编号或 `auto` |
| `--no-overlay` | 禁用悬浮窗 |
| `--no-voice` | 禁用语音 |
| `--fps` | 目标帧率（默认 5） |

---

## 项目结构

```
lol_agent/
├── main.py                        # 主入口，V2 管线编排
├── config.py                      # AgentConfig 集中配置管理
│
├── capture/                       # 屏幕捕获
│   ├── screen_capture.py          # mss 截图 + EnumWindows 模糊匹配
│   └── roi_manager.py             # ROI 裁剪（缓存缩放坐标）
│
├── perception/                    # 感知层
│   ├── yolo_infer.py              # 多模型 YOLO 推理引擎
│   ├── detection_summary.py       # 检测结果分类汇总
│   ├── minimap_parser.py          # OpenCV HSV + HoughCircles（条件触发）
│   └── ocr_engine.py              # PaddleOCR 子进程（base64 管道传输）
│
├── schemas/                       # V2 统一数据规范（Pydantic Schema）
│   ├── hero.py                    # HeroFeature
│   ├── economy.py                 # EconomyFeature
│   ├── skill.py                   # SkillFeature
│   ├── wave.py                    # WaveFeature
│   ├── objective.py               # ObjectiveFeature
│   ├── map.py                     # MapFeature
│   ├── feature_bundle.py          # FeatureBundle（6 合 1）
│   ├── state.py                   # GameStateV2（5 维状态，Literal 类型约束）
│   ├── goal.py                    # Goal（9 种目标，Literal 类型约束）
│   └── decision.py                # Decision（15 种动作，Literal 类型约束）
│
├── memory/                        # 记忆系统
│   ├── hero_memory.py             # 英雄追踪（proximity matching）
│   ├── objective_memory.py        # 中立资源计时（2025/2026 赛季）
│   ├── fight_memory.py            # 团战/死亡事件记录
│   └── temporal_memory.py         # 时序记忆（保留，供未来扩展）
│
├── reasoning/                     # 推理引擎
│   ├── feature_engine.py          # 特征提取（Detection → FeatureBundle）
│   ├── context_engine.py          # 场景识别（7 种上下文）
│   ├── goal_engine.py             # 目标决策（9 种目标 + 置信度）
│   ├── decision_engine_v2.py      # 目标驱动决策（规则映射 + 评分去重）
│   └── llm_engine.py              # Qwen3-8B 本地推理（4-bit 量化）
│
├── utils/                         # 共享工具
│   ├── parsing.py                 # parse_kda / parse_int / parse_time
│   └── map.py                     # classify_lane（对角线距离分类）
│
├── overlay/                       # UI
│   └── overlay_ui.py              # PyQt5 可拖拽透明悬浮窗（V2）
│
├── voice/                         # 语音
│   └── tts_engine.py              # Edge TTS + pyttsx3 fallback
│
├── configs/                       # ROI 配置
│   ├── roi_config.json            # B 站回放/视频布局（1920x1080）
│   └── roi_config_live.json       # 实时游戏布局（1920x1080）
│
├── tests/                         # 测试套件（230 tests）
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

- **模型**: YOLOv12m, 32 classes, 1024px input
- **推理速度**: ~12ms/帧（~83 FPS）
- **训练数据**: 719 张游戏截图
- **权重**: `runs/detect/runs/train/lol_yolo/weights/best.pt`

### 并行管线

YOLO（GPU）与 OCR（CPU 子进程）通过 `ThreadPoolExecutor` 并行执行。OCR 在线程池中运行，同时主线程执行 minimap 解析和 FeatureEngine 提取，总延迟从串行的 YOLO+OCR 降低为 max(YOLO, OCR+Minimap)。

### 帧差跳帧

静止场景（泉水等待、死亡回放）下，帧间差异低于阈值时跳过 YOLO 推理，复用上一帧检测结果，GPU 占用降低 50~80%。

### Context Engine（7 种场景）

| 场景 | 触发条件 |
|---|---|
| retreat | 血量极低 / 被包围无闪现 |
| collapse | 敌方推线 + 人数劣势 |
| contest | 目标即将刷新 + 双方争夺 |
| siege | 兵线推进 + 人数优势 |
| defense | 敌方兵线推进 |
| pressure | 兵线优势 + 敌方消失 |
| safe_farm | 默认安全发育 |

### Goal Engine（9 种战略目标）

`contest_dragon` / `contest_baron` / `contest_herald` / `push_tower` / `defend_tower` / `split_push` / `group` / `retreat` / `farm`

### 中立资源计时（2025/2026 赛季）

| 资源 | 位置 | 首次刷新 | 刷新间隔 |
|---|---|---|---|
| 元素亚龙 | 下河道 | 5:00 | 5:00 |
| 远古巨龙 | 下河道 | 龙魂后 | 10:00 |
| 巢虫 | 上河道 | 5:00 | 一次性 |
| 先锋 | 上河道 | 8:00 | 一次性（19:30 消失） |
| 男爵 | 上河道 | 25:00 | 6:00 |

### 小地图 Lane 分类

使用 (x, y) 双坐标 + 对角线距离判断，而非简单的 Y 坐标三分法。LOL 小地图是对角线布局，mid lane 沿主对角线分布。

### 记忆系统

| 记忆类型 | 功能 |
|---|---|
| HeroMemoryV2 | Proximity matching 追踪英雄，计算失踪时长 |
| ObjectiveMemory | 龙/先锋/男爵击杀/刷新计时，自动检测龙魂 |
| FightMemory | 近期团战胜率、死亡事件 |

### OCR 子进程隔离

PaddleOCR 运行在独立 Python 子进程中，通过 base64 编码图像 + stdin 管道传输（零磁盘 I/O）。原因：PaddlePaddle 与 PyTorch 的 CUDA 绑定在 Windows 下存在类型冲突。OCR 默认使用 CPU 模式。

---

## 测试

```bash
# 全量测试
python -m pytest tests/ -v

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
| V2.0 | Schemas → FeatureEngine → Context/Goal/Decision → LLM → MemoryV2 | ✅ 完成 |
| V2.5 | 等级策略、目标计时修复、debug 模式 | ✅ 完成 |
| V3.0 | 架构重构：删除 V1、Config 管理、并行管线、logging、profiling | ✅ 完成 |
| V3.1 | YOLO+OCR 并行化、帧差跳帧、FightMemory 接入、Dragon Soul 追踪 | ✅ 完成 |
| V4.0 | Transformer 时序预测、EventDetector、OCR 模板匹配 | 🔮 远期 |

---

## 设计原则

1. **Schema 驱动** — 所有模块输入输出基于 Pydantic BaseModel，Literal 类型约束合法值
2. **配置集中** — AgentConfig 统一管理所有阈值/路径/语言，CLI 参数 > 环境变量 > 默认值
3. **共享工具** — utils/parsing.py + utils/map.py 消除重复代码
4. **错误降级** — 单模块异常不影响整体运行，YOLO 失败复用缓存，Engine 失败返回默认值
5. **可观测** — logging + profiling 埋点，debug 模式输出每步耗时

---

## License

MIT
