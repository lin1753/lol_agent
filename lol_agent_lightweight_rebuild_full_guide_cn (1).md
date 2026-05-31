# LOL Agent Assistant 轻量级复刻完整实施文档（RTX4060 个人开发版）

---

# 一、项目定位

本项目目标：

不是实现：

```text
全自动职业LOL AI
```

而是：

# 实时游戏理解 Agent Assistant

即：

- 实时分析LOL画面
- 理解游戏状态
- 维护时序记忆
- 进行规则推理
- 输出危险提醒与战术建议

并且：

- 可在 RTX4060 Laptop 上运行
- 可单人开发
- 不依赖大规模集群
- 不依赖 RL 自博弈
- 不依赖工业级海量数据

---

# 二、最终系统效果

系统运行后：

输入：

```text
LOL实时游戏画面
```

输出：

```text
敌方打野消失 24s
敌方可能正在控龙
下路危险
建议后撤
```

系统能力：

| 功能 | 是否实现 |
|---|---|
| 小地图理解 | YES |
| 英雄识别 | YES |
| 游戏状态维护 | YES |
| 时序记忆 | YES |
| 危险提醒 | YES |
| Overlay显示 | YES |
| 语音提醒 | YES |
| 自然语言解释 | 可选 |
| 自动操作 | NO |
| RL训练 | NO |

---

# 三、项目核心思想（极重要）

真正的 Agent：

不是：

```text
检测到了什么
```

而是：

# 是否维护了“游戏世界状态”

例如：

普通CV：

```text
检测到敌方英雄
```

Agent：

```text
敌方打野已经20秒未出现
```

因此：

本项目核心：

# GameState + Temporal Memory + Rule Engine

而不是：

# 单纯YOLO训练

---

# 四、整体系统架构

完整系统：

```text
LOL Window
    ↓
Screen Capture
    ↓
ROI Manager
    ↓
Perception Layer
(YOLO + OCR)
    ↓
State Parser
    ↓
Temporal Memory
    ↓
Rule Engine
    ↓
Overlay + Voice
    ↓
Optional LLM Layer
```

---

# 五、你当前已有的数据资源

你目前已有：

```text
05_game_heroes_in_view_eval.json
06_game_minimap_heros_understanding_eval.json
hero_name.csv
minimap_labels_v2.json
[images](../lol_yolo/data/images)
[label_xml](../lol_yolo/data/label_xml)
[class_map.txt](../lol_yolo/data/class_map.txt)
```

这些数据已经足够：

# 完成第一版完整 Agent Assistant

重点：

你当前缺少的不是“更多数据”。

而是：

# 状态系统与时序逻辑

---

# 六、项目目录结构（推荐直接使用）

```text
lol_agent/
│
├── data/
│   ├── raw/
│   ├── parsed/
│
├── models/
│   ├── minimap/
│   ├── hero/
│
├── capture/
│   ├── screen_capture.py
│   ├── roi_manager.py
│
├── perception/
│   ├── yolo_infer.py
│   ├── ocr_engine.py
│
├── parser/
│   ├── state_parser.py
│
├── memory/
│   ├── temporal_memory.py
│
├── reasoning/
│   ├── rule_engine.py
│
├── overlay/
│   ├── overlay_ui.py
│
├── voice/
│   ├── tts_engine.py
│
├── configs/
│   ├── roi_config.json
│
├── tests/
│
├── main.py
│
└── requirements.txt
```

---

# 七、开发第一步（最重要）

不要先训练模型。

不要先调YOLO。

第一步：

# 解析你的JSON结构

目标：

理解：

- perception字段
- state字段
- temporal字段

建议：

使用 Claude 协助完成。

---

# 八、Claude JSON解析提示词

直接复制：

```text
帮我分析这个json结构。

目标：
1. 解析字段含义
2. 推断游戏状态语义
3. 使用 pydantic 定义数据结构
4. 输出 dataclass
5. 标注哪些字段属于：
   - perception
   - state
   - temporal
```

---

# 九、必须定义的核心结构：GameState

推荐结构：

```python
class GameState:
    current_time: float

    visible_enemies: list

    visible_allies: list

    minimap_enemy_positions: dict

    minimap_ally_positions: dict

    enemy_missing: list

    dragon_alive: bool

    herald_alive: bool

    baron_alive: bool

    current_gold: int

    player_hp: float

    player_mana: float

    danger_lane: str

    teamfight_probability: float
```

这是整个系统灵魂。

---

# 十、屏幕采集模块（Screen Capture）

推荐库：

# mss

安装：

```bash
pip install mss opencv-python numpy
```

目标：

实时获取LOL窗口画面。

---

# 十一、Claude 提示词：ScreenCapture

```text
帮我写一个高性能LOL实时截图模块。

要求：
1. 使用 mss
2. 返回 numpy array
3. 支持 ROI 截图
4. 支持 1920x1080
5. 封装成 ScreenCapture 类
6. 提供 get_frame()
```

---

# 十二、ROI Manager（核心优化模块）

不要：

# 全屏YOLO

LOL是固定UI布局。

必须：

# ROI分区

---

# 十三、推荐ROI划分

创建：

```text
configs/roi_config.json
```

内容：

```json
{
  "minimap": [0, 780, 300, 300],
  "topbar": [300, 0, 1300, 120],
  "center": [300, 200, 1300, 700],
  "hud": [500, 850, 900, 230]
}
```

---

# 十四、Claude 提示词：ROI Manager

```text
帮我写 LOL ROI Manager。

要求：
1. 从 roi_config.json 读取ROI
2. 支持：
   - minimap_roi
   - center_roi
   - topbar_roi
   - hud_roi
3. 输入 frame
4. 输出裁剪后的numpy array
5. 封装成 ROIManager 类
```

---

# 十五、YOLO 感知层（Perception Layer）

不要：

# 一个模型全做

推荐：

# 多模型方案

---

# 十六、推荐模型结构

## 模型1：Minimap Detector

负责：

- 小地图英雄
- 小地图事件

---

## 模型2：Hero Detector

负责：

- 当前视野英雄
- 团战区域

---

## 模型3（后期）：Objective Detector

负责：

- 小龙
- 先锋
- 大龙

---

# 十七、模型推荐

不要：

```text
yolov8n
```

推荐：

```text
yolov8m
```

原因：

你的任务：

属于：

# 高密度微小目标检测

---

# 十八、推荐训练方案

不要：

```text
1920 + yolov8n
```

推荐：

```text
960 ROI + yolov8m
```

原因：

ROI之后：

目标会自然变大。

---

# 十九、YOLO 推理模块

安装：

```bash
pip install ultralytics
```

---

# 二十、Claude 提示词：YOLO Infer

```text
帮我写 YOLOv8 推理模块。

要求：
1. 使用 ultralytics
2. 支持加载多个模型
3. 支持：
   - minimap model
   - hero model
4. 输入 numpy image
5. 输出：
   - class
   - confidence
   - bbox
6. 支持 FP16
7. 支持 GPU CUDA
```

---

# 二十一、OCR 模块

LOL大量信息属于数字。

例如：

- 时间
- KDA
- 金币
- 等级
- 技能CD

推荐：

# PaddleOCR

安装：

```bash
pip install paddleocr
```

---

# 二十二、State Parser（系统真正核心）

State Parser：

负责：

# 把YOLO/OCR结果转成游戏状态

---

# 二十三、示例

YOLO输出：

```json
[
  {
    "class": "enemy",
    "x": 233,
    "y": 512
  }
]
```

State Parser输出：

```json
{
  "enemy_visible": true,
  "enemy_count": 1,
  "danger_lane": "bot"
}
```

---

# 二十四、Claude 提示词：State Parser

```text
帮我写 LOL State Parser。

输入：
1. minimap detections
2. hero detections
3. OCR结果

输出：
GameState

要求：
1. 统计 visible enemies
2. 统计 visible allies
3. 判断 enemy missing
4. 维护 hero positions
5. 输出结构化状态
```

---

# 二十五、Temporal Memory（真正Agent感来源）

这是：

# 系统开始“理解LOL”的地方

核心思想：

维护：

# 历史状态

而不是：

# 单帧结果

---

# 二十六、Temporal Memory 示例

```python
last_seen["leesin"] = {
    "time": 312,
    "position": "top_river"
}
```

系统才能推理：

```text
敌方打野可能正在控先锋
```

---

# 二十七、Claude 提示词：Temporal Memory

```text
帮我写 LOL Temporal Memory 系统。

功能：
1. 记录英雄最后出现时间
2. 记录最后出现位置
3. 计算 missing duration
4. 维护最近30秒状态
5. 支持 update(GameState)
6. 支持 get_enemy_missing()
```

---

# 二十八、Rule Engine（最适合个人开发）

不要：

# Transformer

不要：

# RL

推荐：

# Rule-based Reasoning

原因：

LOL：

属于：

# 高规则性游戏

大量推理：

本身就是显式规则。

---

# 二十九、推荐规则

## 规则1：打野消失

```python
if enemy_jg_missing > 20:
    warning("注意敌方打野")
```

---

## 规则2：多人消失

```python
if missing_enemy_count >= 3:
    warning("敌方可能正在集结")
```

---

## 规则3：龙刷新

```python
if dragon_spawn < 30:
    warning("准备控龙")
```

---

# 三十、Claude 提示词：Rule Engine

```text
帮我写 LOL Rule Engine。

输入：
1. GameState
2. TemporalMemory

输出：
warnings list

规则：
1. enemy_jg_missing
2. multiple_enemy_missing
3. dragon_warning
4. danger_lane
5. teamfight_warning
```

---

# 三十一、Overlay UI（Agent感暴涨）

推荐：

# PyQt5

安装：

```bash
pip install pyqt5
```

---

# 三十二、Overlay 示例

右上角显示：

```text
[Warning]
敌方多人消失
```

---

# 三十三、Claude 提示词：Overlay UI

```text
帮我写 LOL Overlay UI。

要求：
1. 使用 PyQt5
2. 透明背景
3. 永远置顶
4. 支持显示 warning list
5. 右上角显示
6. 支持实时更新
```

---

# 三十四、语音系统（推荐）

推荐：

- pyttsx3
- Edge TTS

安装：

```bash
pip install pyttsx3
```

---

# 三十五、Claude 提示词：TTS Engine

```text
帮我写 LOL TTS Engine。

要求：
1. 使用 pyttsx3
2. 支持异步播报
3. 避免重复播报
4. 支持 warning queue
```

---

# 三十六、主程序 main.py

最终运行流程：

```text
capture
    ↓
ROI
    ↓
YOLO
    ↓
OCR
    ↓
StateParser
    ↓
TemporalMemory
    ↓
RuleEngine
    ↓
Overlay
    ↓
Voice
```

---

# 三十七、Claude 提示词：main.py

```text
帮我整合 LOL Agent Assistant。

要求：
1. 实时循环
2. ScreenCapture
3. ROIManager
4. YOLOInfer
5. StateParser
6. TemporalMemory
7. RuleEngine
8. OverlayUI
9. TTS
10. 支持 Ctrl+C退出
11. 支持 FPS统计
```

---

# 三十八、推荐开发顺序

## 第1周

完成：

```text
截图 → ROI → YOLO
```

---

## 第2周

完成：

```text
State Parser
```

---

## 第3周

完成：

```text
Temporal Memory
```

---

## 第4周

完成：

```text
Rule Engine
```

---

## 第5周

完成：

```text
Overlay + TTS
```

---

# 三十九、为什么现在不做 Transformer

因为：

Transformer需要：

- trajectory dataset
- 时序标签
- 大量对局录像
- 战术行为标注

而你现在拥有的是：

# perception dataset

因此：

Rule Engine 更适合。

---

# 四十、LLM（Qwen3-8B）的正确位置

Qwen：

不适合：

# 实时核心推理

适合：

# 语言解释层

例如：

输入：

```json
{
  "enemy_missing": 4,
  "dragon_spawn": 15
}
```

输出：

```text
敌方多人消失，小龙即将刷新，建议提前布置河道视野。
```

因此：

正确架构：

```text
Rule Engine（实时）
+
LLM（解释层）
```

---

# 四十一、真正的开发重点（非常重要）

不要继续卷：

# 模型大小

真正重要的是：

# 游戏世界状态维护

因此：

真正优先级：

| 优先级 | 模块 |
|---|---|
| 1 | State System |
| 2 | Temporal Memory |
| 3 | Rule Engine |
| 4 | Overlay体验 |
| 5 | YOLO优化 |

---

# 四十二、最终可实现效果（4060 Laptop）

你的系统完全可以实现：

- 实时小地图理解
- 实时危险提醒
- 实时地图意识分析
- 实时战术提示
- 半实时自然语言解释

并且：

# 5~10FPS 完全可行

---

# 四十三、方案A完整任务列表（RTX4060 实施版）

---

# 项目总目标

最终实现：

```text
LOL画面
    ↓
实时检测
    ↓
游戏状态理解
    ↓
危险判断
    ↓
Overlay + 语音提醒
```

实现：

- 小地图识别
- 英雄识别
- 时序状态维护
- 危险提醒
- Rule Engine
- Overlay Assistant

不实现：

- 自动操作
- RL
- 自动补刀
- Transformer Policy
- 职业级AI

---

# 完整开发阶段

| 阶段 | 名称 | 目标 |
|---|---|---|
| Phase 1 | 输入流系统 | 稳定截图 + ROI |
| Phase 2 | 感知层 | YOLO实时检测 |
| Phase 3 | 状态系统 | GameState |
| Phase 4 | 时序记忆 | Temporal Memory |
| Phase 5 | 推理层 | Rule Engine |
| Phase 6 | Agent输出 | Overlay + TTS |
| Phase 7 | 系统优化 | FPS/稳定性 |
| Phase 8 | 可选增强 | LLM解释层 |

---

# Phase 1：输入流系统

目标：

```text
LOL实时截图
→ ROI裁剪
→ OpenCV显示
```

## Task 1.1：创建项目结构

- [ ] 创建 Conda 环境
- [ ] 安装 Python 3.10
- [ ] 创建项目目录
- [ ] 创建 requirements.txt

## Task 1.2：安装基础依赖

- [ ] torch
- [ ] ultralytics
- [ ] opencv-python
- [ ] mss
- [ ] numpy

验证：

- [ ] CUDA可用
- [ ] torch识别4060

## Task 1.3：Screen Capture

文件：

```text
capture/screen_capture.py
```

功能：

- [ ] 实时截图
- [ ] 获取全屏frame
- [ ] ROI截图
- [ ] OpenCV格式输出
- [ ] FPS统计

验证标准：

- [ ] 能实时看到LOL窗口
- [ ] FPS ≥ 30

## Task 1.4：ROI Manager

文件：

```text
capture/roi_manager.py
```

功能：

- [ ] 读取 roi_config.json
- [ ] 裁剪 minimap ROI
- [ ] 裁剪 center ROI
- [ ] 裁剪 topbar ROI
- [ ] 裁剪 hud ROI

验证标准：

- [ ] minimap位置正确
- [ ] center区域正确
- [ ] ROI无偏移

---

# Phase 2：Perception Layer（YOLO）

目标：

```text
ROI
→ YOLO
→ 实时检测结果
```

## Task 2.1：YOLO 推理模块

文件：

```text
perception/yolo_infer.py
```

功能：

- [ ] 加载 best.pt
- [ ] GPU推理
- [ ] FP16推理
- [ ] 输出bbox
- [ ] 输出class
- [ ] 输出confidence

验证标准：

- [ ] 实时检测稳定
- [ ] FPS ≥ 5

## Task 2.2：Minimap Detector

功能：

- [ ] 小地图英雄识别
- [ ] 小地图事件识别

验证标准：

- [ ] 小地图英雄稳定检测
- [ ] 不频繁漏检

## Task 2.3：Center Hero Detector

功能：

- [ ] 当前视野英雄识别
- [ ] 血条区域检测

验证标准：

- [ ] 团战时可检测
- [ ] 多英雄不严重错检

---

# Phase 3：GameState 系统

目标：

```text
检测结果
→ 游戏状态
```

## Task 3.1：定义 GameState

文件：

```text
parser/game_state.py
```

功能：

- [ ] HeroState
- [ ] ObjectiveState
- [ ] PlayerState
- [ ] MinimapState

推荐字段：

- [ ] visible_enemies
- [ ] visible_allies
- [ ] enemy_positions
- [ ] player_hp
- [ ] current_time
- [ ] dragon_alive

## Task 3.2：State Parser

文件：

```text
parser/state_parser.py
```

功能：

- [ ] YOLO结果解析
- [ ] OCR结果解析
- [ ] 构建GameState
- [ ] 输出结构化状态

验证标准：

- [ ] 正确统计敌方人数
- [ ] 正确识别当前位置
- [ ] 正确输出状态JSON

---

# Phase 4：Temporal Memory

目标：

```text
记住过去发生了什么
```

## Task 4.1：Temporal Memory

文件：

```text
memory/temporal_memory.py
```

功能：

- [ ] last_seen_time
- [ ] last_seen_position
- [ ] missing_duration
- [ ] recent_positions
- [ ] state history

## Task 4.2：时序稳定化

功能：

- [ ] 多帧确认
- [ ] Confidence Voting
- [ ] TTL机制
- [ ] Temporal Smoothing

验证标准：

- [ ] enemy_missing 不抖动
- [ ] 英雄不会瞬间消失

---

# Phase 5：Rule Engine

目标：

```text
游戏理解
→ 危险判断
```

## Task 5.1：Rule Engine 基础框架

文件：

```text
reasoning/rule_engine.py
```

功能：

- [ ] 输入 GameState
- [ ] 输入 TemporalMemory
- [ ] 输出 warning list

## Task 5.2：核心规则

必做规则：

- [ ] enemy_jg_missing
- [ ] multiple_enemy_missing
- [ ] dragon_spawn_warning
- [ ] danger_lane
- [ ] teamfight_warning

---

# Phase 6：Overlay + Voice

目标：

```text
实时战术提醒
```

## Task 6.1：Overlay UI

文件：

```text
overlay/overlay_ui.py
```

功能：

- [ ] 透明窗口
- [ ] 永远置顶
- [ ] 显示warning
- [ ] 实时刷新

技术：

- [ ] PyQt5

## Task 6.2：TTS语音提醒

文件：

```text
voice/tts_engine.py
```

功能：

- [ ] warning播报
- [ ] 避免重复播报
- [ ] warning queue

---

# Phase 7：系统优化

目标：

提升：

```text
稳定性 + FPS
```

## Task 7.1：异步流水线

功能：

- [ ] capture thread
- [ ] infer thread
- [ ] UI thread

## Task 7.2：FPS优化

功能：

- [ ] ROI优化
- [ ] FP16
- [ ] batch=1
- [ ] CUDA stream

## Task 7.3：稳定性优化

功能：

- [ ] 防止Overlay卡死
- [ ] 防止线程阻塞
- [ ] 防止内存泄漏

---

# Phase 8：LLM解释层（可选）

目标：

```text
规则结果
→ 自然语言战术建议
```

## Task 8.1：Qwen3-8B 接入（可选）

输入：

```json
{
  "enemy_missing": 4,
  "dragon_spawn": 15
}
```

输出：

```text
敌方多人消失，小龙即将刷新，建议提前布置河道视野。
```

---

# 当前真正优先级

## 第一优先级

```text
Capture + ROI
```

## 第二优先级

```text
YOLO实时推理
```

## 第三优先级

```text
GameState
```

## 第四优先级

```text
Temporal Memory
```

## 第五优先级

```text
Rule Engine
```

---

# 当前不做的内容

不要做：

- [ ] RL
- [ ] 自动操作
- [ ] 自动补刀
- [ ] 多智能体
- [ ] DETR
- [ ] Transformer Policy
- [ ] 行为克隆
- [ ] 端到端Agent

---

# 最终目标（现实版）

4060 Laptop 最终目标：

| 指标 | 目标 |
|---|---|
| FPS | 5~10 |
| 延迟 | <200ms |
| 小地图检测 | 稳定 |
| 状态维护 | 稳定 |
| Overlay | 实时 |
| 语音提醒 | 正常 |

---

# 四十四、最终结论

你当前：

已经脱离：

# “YOLO练手项目”

阶段。

你现在真正进入的是：

# 游戏状态建模（Game State Modeling）

阶段。

而真正的 Agent：

核心永远不是：

# 模型大小

而是：

# 世界状态是否被正确维护。

