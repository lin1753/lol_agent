# LOL Agent Assistant 开发进度

## 总览

| Phase | 模块 | 状态 | 测试 | 备注 |
|---|---|---|---|---|
| 0 | 项目初始化 | ✅ 完成 | PASS | 2026-05-28 |
| 1 | 数据解析与理解 | ✅ 完成 | PASS | 2026-05-28 |
| 2 | 屏幕捕获 + ROI | ✅ 完成 | PASS | 2026-05-29 |
| 3 | YOLO 感知层 | ✅ 完成 | PASS | 2026-05-29 |
| 4 | OCR 引擎 | ✅ 完成 | PASS | 2026-05-29 |
| 5 | GameState 定义 | ✅ 完成 | PASS | 2026-05-29 |
| 6 | 状态解析器 | ✅ 完成 | PASS | 2026-05-29 |
| 7 | 时序记忆 | ✅ 完成 | PASS | 2026-05-29 |
| 8 | 规则引擎 | ✅ 完成 | PASS | 2026-05-29 |
| 9 | Overlay UI | ✅ 完成 | PASS | 2026-05-29 |
| 10 | 语音系统 | ✅ 完成 | PASS | 2026-05-29 |
| 11 | 主程序集成 | ✅ 完成 | PASS | 2026-05-29 |
| 12 | 系统优化 | 待开始 | - | |
| 13 | 重建 center_yolo 数据集 | ✅ 完成 | PASS | 2026-05-29 |
| 14 | 新建 minimap_parser | ✅ 完成 | PASS | 2026-05-29 |
| 15 | 更新双数据源集成 | ✅ 完成 | PASS | 2026-05-29 |
| 16 | 29类 YOLO 训练 | ✅ 完成 | mAP50=87.1% | 2026-05-30 |
| 17 | YOLO-guided OCR | ✅ 完成 | PASS | 2026-05-30 |
| 18 | Overlay 可拖动+OCR优化 | ✅ 完成 | PASS | 2026-05-30 |
| 19 | State Understanding Engine | ✅ 完成 | PASS | 2026-05-31 |
| 20 | Decision Engine (20规则) | ✅ 完成 | PASS | 2026-05-31 |
| 21 | Overlay 状态面板升级 | ✅ 完成 | PASS | 2026-05-31 |
| 22 | OCR 缓存 + Overlay 修复 | ✅ 完成 | PASS | 2026-05-31 |
| 23 | OCR 子进程修复 + 预处理优化 | ✅ 完成 | PASS | 2026-05-31 |
| 24 | Overlay 加入实时游戏时间 | ✅ 完成 | PASS | 2026-05-31 |

---

## Phase 0：项目初始化

**状态**：✅ 完成

### 任务清单
- [x] 创建目录结构（capture/, perception/, parser/, memory/, reasoning/, overlay/, voice/, configs/, models/, tests/, data/, scripts/, docs/）
- [x] 创建 pyproject.toml（含 dev 依赖组、Black/Ruff/Pytest 配置）
- [x] 各包目录已添加 __init__.py
- [x] 验证 CUDA 环境

### 测试报告
- **CUDA**: ✅ `torch.cuda.is_available() = True`，设备：NVIDIA GeForce RTX 4060 Laptop GPU
- **torch**: 2.5.1+cu121
- **pydantic**: 2.13.4
- **opencv**: 4.10.0
- **numpy**: 2.2.6
- **ultralytics**: 8.4.56
- **Conda 环境**: `lol_agent`（`D:\Tools\Anaconda_envs\envs\lol_agent`）

---

## Phase 1：数据解析与理解

**状态**：✅ 完成

### 任务清单
- [x] 解析 05_game_heroes_in_view_eval.json（391 条，英雄视野 VQA）
- [x] 解析 06_game_minimap_heros_understanding_eval.json（415 条，小地图 VQA）
- [x] 解析 hero_name.csv（173 个英雄，拼音ID/中文名/昵称）
- [x] 解析 class_map.txt（48 类，UTF-16，覆盖 UI/英雄/野怪/技能/眼位）
- [x] 分析 images/（719 张 1920×1080 JPG）和 label_xml/（719 个 VOC XML）
- [x] 输出 docs/data_schema.md

### 测试报告
- **数据完整性**: ✅ 719 张图片 ↔ 719 个 XML 标注一一对应
- **类别数**: 48 类（UI 元素 20+、英雄相关 6、小兵 4、防御塔 2、野怪 11、技能 7、眼位 4）
- **分析脚本**: `scrip
- ts/analyze_data.py` 可正常加载并输出所有数据结构摘要
- **关键发现**: 单图平均标注 20-30 个目标；VQA 数据可用于后续 LLM 解释层微调

---

## Phase 2：屏幕捕获 + ROI

**状态**：✅ 完成

### 交付文件
- `capture/screen_capture.py` — ScreenCapture 类（mss 截图、LOL 窗口自动检测、上下文管理器）
- `capture/roi_manager.py` — ROIManager 类（配置文件加载、区域裁剪、缩放支持）
- `configs/roi_config.json` — ROI 区域定义（minimap/topbar/center/hud）
- `tests/test_capture.py` — 15 个测试用例

### 测试报告
- **15/15 通过**，0 warning
- 覆盖：Region 坐标计算、4 个 ROI 区域形状验证、像素值保持、裁剪副本独立性、JSON 配置加载、非标准分辨率缩放、ScreenCapture 实例化和上下文管理器
- 关键验证：1920×1080 和 960×540 两种分辨率下 ROI 裁剪均正确

---

## Phase 3：YOLO 感知层

**状态**：✅ 完成

### 交付文件
- `perception/yolo_infer.py` — YoloInfer 类（多模型加载、FP16、CUDA、Detection 数据类）
- `scripts/convert_voc_to_yolo.py` — VOC XML → YOLO 格式转换（48 类映射、train/val 拆分）
- `scripts/train_yolo.py` — YOLO 训练脚本（ultralytics 封装）
- `tests/test_perception.py` — 8 个测试用例

### 测试报告
- **8/8 通过**
- **数据转换**: 719 张图片 → 575 train + 144 val（80/20 拆分）
- **YOLO 标签验证**: 48 类映射正确，归一化坐标范围 [0,1]
- **YoloInfer**: 初始化正常，未加载模型时正确抛出 ValueError
- **训练脚本**: 已就绪，执行 `python scripts/train_yolo.py --epochs 100 --batch 8` 可开始训练
- **注意**: 实际 YOLO 训练需要用户手动执行（耗时较长，需 GPU 持续运行）

---

## Phase 4：OCR 引擎

**状态**：✅ 完成

### 交付文件
- `perception/ocr_engine.py` — OcrEngine 类（子进程隔离 PaddleOCR，避免 PyTorch CUDA 冲突）
- `tests/test_ocr.py` — 8 个测试用例

### 测试报告
- **8/8 通过**
- 覆盖：OcrResult 坐标计算、引擎初始化、空图片识别、number/time/KDA 解析、真实游戏截图 OCR
- **实际识别效果**: 成功识别 KDA `0/0/0`、游戏时间 `00:12`、中文 UI 文本
- **环境修复**: PaddleOCR 降级至 2.10.0 + albumentations 降级至 1.3.1 + 安装 nvidia-cudnn-cu12 8.9.7.29
- **GPU 支持**: 自动添加 NVIDIA DLL 路径（cuDNN 8/cuBLAS/nvrtc），PaddlePaddle GPU 推理正常

---

## Phase 5：GameState 定义

**状态**：✅ 完成

### 交付文件
- `models/game_state.py` — GameState pydantic 模型（含 HeroPosition、ObjectiveStatus、Team 枚举）
- `tests/test_game_state.py` — 11 个测试用例

### 测试报告
- **11/11 通过**
- 覆盖：默认状态、数据填充、JSON 序列化/反序列化、minimap 位置查询、HP/概率范围验证、Objective 状态
- GameState 字段：current_time, visible_enemies/allies, minimap_positions, enemy_missing, dragon/herald/baron, player_hp/mana/gold/level, KDA, danger_lane, teamfight_probability, towers

---

## Phase 6：状态解析器

**状态**：✅ 完成

### 交付文件
- `parser/state_parser.py` — StateParser 类（YOLO 检测 + OCR → GameState）
- `tests/test_state_parser.py` — 9 个测试用例

### 测试报告
- **9/9 通过**
- 覆盖：空输入、时间/KDA/数字解析、英雄分类（敌方/友方）、minimap 检测、OCR 解析、完整端到端解析、线路估算
- 核心逻辑：英雄队伍推断（绿/蓝血条=友方，红血条=敌方）、线路估算（top/mid/bot/jungle）、团战概率计算（3+英雄聚集）

---

## Phase 7：时序记忆

**状态**：✅ 完成

### 交付文件
- `memory/temporal_memory.py` — TemporalMemory 类（HeroMemory、滑动窗口、轨迹追踪）
- `tests/test_temporal_memory.py` — 10 个测试用例

### 测试报告
- **10/10 通过**
- 覆盖：空状态、英雄追踪、缺席时长计算、英雄重现、轨迹记录与上限、30 帧窗口、打野缺席、多人缺席排序、清除
- 核心功能：每英雄 last_seen_time + missing_duration、30 秒滑动窗口、按缺席时长排序

---

## Phase 8：规则引擎

**状态**：✅ 完成

### 交付文件
- `reasoning/rule_engine.py` — RuleEngine 类（6 条规则 + 去重机制）
- `tests/test_rule_engine.py` — 10 个测试用例

### 测试报告
- **10/10 通过**
- 规则列表：打野缺席(>20s)、多人缺席(≥3)、小龙刷新提醒、危险线路、团战概率(≥0.6)、低血量(≤20%)
- 覆盖：空状态无警告、各规则独立触发、去重机制、clear_recent 重置、多规则同时触发
- 警告级别：info(蓝)/warn(黄)/danger(红)

---

## Phase 9：Overlay UI

**状态**：✅ 完成

### 交付文件
- `overlay/overlay_ui.py` — OverlayUI 控制器 + OverlayWidget（PyQt5 透明悬浮窗）
- `tests/test_overlay.py` — 8 个测试用例

### 测试报告
- **8/8 通过**
- 覆盖：颜色映射完整性、级别值、导入、初始化、停止安全、Warning 创建与哈希
- OverlayWidget 特性：透明背景、永远置顶、无边框、不拦截鼠标事件、圆角暗色背景、自适应高度

---

## Phase 10：语音系统

**状态**：✅ 完成

### 交付文件
- `voice/tts_engine.py` — TtsEngine 类（Edge TTS + pygame 播放 + pyttsx3 备用）
- `tests/test_tts.py` — 7 个测试用例

### 测试报告
- **7/7 通过**
- 覆盖：初始化、启停、去重机制、去重清除、Warning 级别过滤、重复消息去重
- 核心功能：Edge TTS（zh-CN-YunxiNeural）生成中文语音 + pygame 播放、10 秒去重窗口、warn+danger 级别播报
- 依赖：edge-tts、pygame（已安装）
- 备用：若 edge-tts 不可用自动回退 pyttsx3

---

## Phase 11：主程序集成

**状态**：✅ 完成

### 交付文件
- `main.py` — LolAgent 主类 + CLI 入口（串联全部模块）
- `tests/test_main.py` — 3 个测试用例

### 测试报告
- **3/3 通过**（单模块）
- **81/81 全量回归通过**（排除 OCR 单独测试）
- 覆盖：模块导入、CPU 无模型初始化、全链路集成（检测→解析→记忆→规则）
- LolAgent 功能：自动 LOL 窗口检测、实时循环（capture→ROI→YOLO+OCR→StateParser→TemporalMemory→RuleEngine→Overlay+Voice）、FPS 统计、Ctrl+C 优雅退出
- CLI 参数：`--model`, `--no-overlay`, `--no-voice`, `--monitor`, `--fps`, `--cpu`
- 启动命令：`python main.py --model path/to/best.pt`
- 修复：PaddleOCR 改为延迟导入，避免与 PyTorch CUDA 冲突

---

## 双数据源架构升级

**状态**：✅ 完成（2026-05-29）

### 变更说明
根据 `lol_agent_final_feasible_plan_cn.md` 方案，将单 YOLO 48 类改为：
- **Center YOLO**（YOLOv8m, 960px）：仅检测主视野 5 类（绿/蓝/红血条英雄 + 红/蓝小兵）
- **Minimap Parser**（OpenCV 颜色分割）：检测小地图英雄位置，无需 YOLO 模型

### 交付文件
- `perception/minimap_parser.py` — MinimapParser 类（HSV 颜色分割，30-50 FPS）
- `scripts/build_center_dataset.py` — 从 XML 提取 center 区域 5 类数据集
- `parser/state_parser.py` — 新增 `parse_with_minimap()` 方法
- `main.py` — 更新为双数据源路由（YOLO center + OpenCV minimap）
- `tests/test_minimap_parser.py` — 8 个测试用例

### 测试报告'
- **minimap_parser**: 8/8 通过，真实图片检测到 1 敌方 + 1 友方
- **center 数据集**: 612 张有效图片 → 489 train / 123 val（5 类）
- **集成测试**: 20/20 通过（main + state_parser + minimap_parser）
- **center_yolo 训练**: 待用户启动（`python scripts/train_yolo.py --data data/center_dataset/dataset.yaml --model yolov8m --imgsz 960 --batch 4`）

---

## 29 类 YOLO 训练（2026-05-30）

**状态**：✅ 完成

### 模型信息
- **模型**: YOLOv8m, 93 layers, 25.8M 参数
- **输入**: 1024px 全屏
- **推理速度**: 14ms/帧（~71 FPS）

### 训练结果
- **mAP50**: 87.1% | **mAP50-95**: 73.1% | **Precision**: 91.0% | **Recall**: 85.2%
- **优秀类别（>95% mAP50）**: game_time(99.5%), gold(99.5%), minimap(99.5%), Q/W/E/R/D/F skills(98-99%), KDA(97.9%), 英雄血条(97-98%), minimap_fov(98.8%), player_level(99.5%)
- **弱项**: baron(0%, 样本仅 2), red_tower(48.9%), blue_cannon(52.3%)
- **数据集**: `data/center_29_dataset/` (575 train / 124 val, 719 张全量图片)
- **权重**: `runs/detect/runs/train/lol_yolo/weights/best.pt`

---

## YOLO-guided OCR + Overlay 优化（2026-05-30）

**状态**：✅ 完成

### 架构变更
- YOLO 全屏检测 29 类 → 自动定位 UI 元素（game_time, KDA, gold, level）
- OCR 根据 YOLO bbox 裁剪区域 → 预处理（二值化+膨胀）→ 识别
- **消除固定 ROI 依赖**，适配视频/直播等非标布局

### 交付文件
- `perception/detection_summary.py` — DetectionSummary 汇总 + extract_ocr_regions + OCR 预处理
- `overlay/overlay_ui.py` — OverlayWidget 支持鼠标拖拽移动
- `configs/roi_config.json` — 更新为 Bilibili 视频布局
- `configs/roi_config_live.json` — 实时游戏布局配置

### 测试报告
- **11/11 通过**（overlay + main）
- **OCR 预处理**: 处理后速度从 4.4s → 0.0s，准确率保持
- **Overlay 拖拽**: set_warnings 不再重置位置（使用 self.pos() 保留当前位置）

### 已知限制
- 视频中 bbox 位置可能因画面变化而微调 → 视频特有问题，实时游戏不受影响
- OCR 偶尔漏读 → 可缓存上次成功值作为 fallback

---

## Rule Engine 优化：State Understanding + Decision Engine（2026-05-30）

**状态**：进行中

### 架构设计（基于 `Rule Engine优化.md`）

```
GameState + TemporalMemory
    ↓
State Understanding Engine（状态理解）
  ├─ PhaseEngine: 游戏阶段（early/mid/late）
  ├─ ContextEngine: 场景识别（laning/split_push/skirmish/teamfight/dragon_fight/baron_fight）
  ├─ CombatEngine: 战斗态势（advantage/even/disadvantage）
  ├─ LaneEngine: 兵线态势（pushing/being_pushed/neutral）
  ├─ ThreatEngine: 威胁分析（low/medium/high）
  └─ ObjectiveEngine: 目标计时器（龙/男爵/先锋）
    ↓
Decision Engine（决策引擎，20 条规则）
  ├─ 一级提醒（Alert）: 10 条
  └─ 二级建议（Suggestion）: 10 条
    ↓
Overlay 状态面板 + Voice
```

### 任务拆分
- [x] Task 1：扩展 GameState 模型
- [x] Task 2：新建 State Understanding Engine（18/18 测试）
- [x] Task 3：升级 Decision Engine（14/14 测试）
- [x] Task 4：更新 StateParser 适配新引擎
- [x] Task 5：升级 Overlay UI 状态面板（8/8 测试）
- [x] Task 6：更新主程序和测试（111/111 全量通过）

### 测试报告
- **GameState**: 11/11 通过
- **StateEngine**: 18/18 通过（Phase/Context/Combat/Lane/Threat/Objective 6 子引擎）
- **DecisionEngine**: 14/14 通过（10 提醒 + 10 建议，去重机制）
- **Overlay**: 8/8 通过（状态面板 + 拖拽 + 动态高度）
- **全量回归**: 111/111 通过

### 后续修复（2026-05-31）
- **OCR 缓存**: `ocr_values` 从 `_cached_ocr` 初始化，OCR 成功时更新缓存，失败时保留上次值 → 游戏时间不再重置为 0
- **Overlay 精简**: 目标计时器仅在距刷新 ≤120s 时显示，警告最多显示 5 条，面板自适应高度
- **OCR 子进程修复**: 临时文件唯一化（避免并发冲突）、崩溃自动恢复、去掉有害二值化预处理
- **Overlay 加入实时游戏时间**: 面板顶部大字显示 `⏱ MM:SS`
