# LOL Agent Assistant（最终可实现方案）

## 基于现有资源：RTX4060 + 719张截图 + XML标注 + 05/06语义数据 + minimap_labels_v2

---

# 一、项目最终目标

实现一个可运行的轻量级LOL Agent：

- 可实时运行
- 能理解游戏状态
- 实时危险提醒
- 小地图及主视野敌我位置跟踪
- Overlay显示及TTS语音输出
- 完全基于现有数据，无需新增人工标注

---

# 二、数据资源分析

| 数据源 | 实际用途 |
|---|---|
| 719张1920x1080截图 | 原始视觉输入 |
| XML标注 | Detection训练核心（主视野、血条、小兵、炮车、塔） |
| 05_game_heroes_in_view_eval.json | 主视野英雄语义验证 |
| 06_game_minimap_heros_understanding_eval.json | 小地图英雄语义验证 |
| minimap_labels_v2.json | 小地图空间位置逻辑 |
| class_map.txt | Detection类别映射 |

**说明**：
- XML包含主视野bbox，但HUD头像、真眼、假眼不在小地图中。
- 05/06是Image-Level Label，用于验证而非训练。
- 小地图真实检测无需YOLO，可使用OpenCV解析。

---

# 三、系统架构（最终版）

```text
Screen Capture
      ↓
 ┌─────────────┐
 │             │
 ↓             ↓
center_yolo   minimap_parser(OpenCV)
 │             │
 └──────┬──────┘
        ↓
    GameState
        ↓
 Temporal Memory
        ↓
   Rule Engine
        ↓
 Overlay / TTS
```

---

# 四、模块说明

### 1. Capture & ROI
- 实时截图全屏
- ROI裁剪：
  - minimap: 320x320
  - center: 960px
- FPS统计

### 2. center_yolo
- 数据来源：XML
- 输入：中心视野ROI
- 类别：英雄血条、小兵、炮车、防御塔
- 输出：bbox + class
- 训练参数：
  - 模型：YOLOv8m
  - imgsz: 960
  - batch: 4~8
  - epochs: 100
  - AMP FP16
  - Early stopping: patience=20

### 3. minimap_parser
- 技术：OpenCV模板匹配或颜色分割
- 输入：320x320小地图ROI
- 解析：
  - 小地图英雄位置
  - 敌我阵营
  - 野区目标
- 数据来源：minimap_labels_v2 + 06.json验证

### 4. GameState
- 整合YOLO输出与小地图解析结果
- 输出结构化状态：
  ```json
  {
    "visible_enemy_count": 3,
    "enemy_positions": [...],
    "ally_positions": [...],
    "dragon_alive": true
  }
  ```

### 5. Temporal Memory
- 追踪目标过去出现位置
- 记录last_seen_time、recent_positions、missing_duration

### 6. Rule Engine
- 核心逻辑：
  - 敌方打野消失
  - 多敌包夹
  - 龙刷新提醒
- 示例：
  ```python
  if enemy_jg_missing > 20:
      warning("敌方打野可能在附近")
  if dragon_spawn < 40:
      warning("小龙即将刷新")
  if 4 enemy missing:
      warning("敌方可能包夹")
  ```

### 7. Overlay + TTS
- 技术：PyQt5 + pyttsx3
- 显示实时警告信息
- 播报语音提示

---

# 五、训练数据处理方案（Claude可执行）

1. 读取XML
2. 对bbox进行中心视野ROI裁剪
3. 转换为YOLO txt格式
4. 分train/val
5. 生成训练目录：
   ```
   datasets/center/
   datasets/minimap/ (用于验证或模板匹配)
   ```

---

# 六、推理性能（4060 Laptop预期）

| 模块 | FPS |
|------|-----|
| center_yolo | 8~15 |
| minimap_parser | 30~50 |
| 整体系统 | 5~10 |

---

# 七、最终方案特点

- 不训练小地图YOLO，避免无bbox问题
- 单模型center_yolo负责主视野检测
- 小地图解析使用OpenCV模板匹配
- 使用现有XML与minimap_labels_v2即可实现完整Agent
- 05/06 JSON仅做验证与状态校验
- 完全符合现有资源条件，可在单机RTX4060运行

---

# 八、开发目录结构（推荐）

```
lol_agent/
├── datasets/
│   ├── center/
│   └── minimap/
├── models/
│   └── center_yolo.pt
├── capture/
├── perception/
│   └── center_yolo.py
├── parser/
│   └── game_state.py
├── memory/
│   └── temporal_memory.py
├── reasoning/
│   └── rule_engine.py
├── overlay/
│   └── overlay_ui.py
├── voice/
│   └── tts_engine.py
├── configs/
│   └── roi_config.json
└── main.py
```

---

# 九、最终结论

基于你现有的：

- XML bbox
- 719张截图
- 05/06语义数据
- minimap_labels_v2
- RTX4060
- Conda环境

你已经完全具备实现一个**完整可运行轻量级LOL Agent**的条件。

- YOLO仅用于主视野目标检测
- 小地图解析用OpenCV
- GameState + Temporal Memory + Rule Engine提供核心Agent逻辑
- Overlay/TTS提供实时交互和提醒

这是当前资源条件下**最稳妥、可实现、工业逻辑合理**的方案。

