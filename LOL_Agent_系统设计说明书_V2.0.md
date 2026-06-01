# LOL Agent Assistant 系统设计说明书 V2.0

## 1. 项目定位

### 项目目标

构建一个基于 YOLO + Game State + Tactical Engine + Qwen3-8B 的 LOL Agent Assistant。

目标效果参考：

- 王者荣耀内置游戏助手
- 英雄联盟复盘助手
- 战术分析助手

但不进行自动操作游戏。

系统职责：

- 感知游戏状态
- 理解游戏局势
- 分析战术目标
- 生成实时建议
- 语音提醒关键事件

---

# 2. 当前资源盘点

## 已拥有数据

### 检测数据

- 719张训练图片
- XML标注文件
- YOLO训练集

### 语义数据

05文件：

- 当前画面出现英雄名称

06文件：

- 小地图英雄名称

### 已训练模型

YOLOv8

mAP50 ≈ 87%

### 硬件

RTX4060 Laptop

适合：

- YOLO实时推理
- OCR
- Qwen3-8B推理

---

# 3. 最终系统架构

Screen Capture
↓
YOLO Detector
↓
Feature Engine
↓
Memory Engine
↓
Game Understanding Engine
↓
Goal Engine
↓
Decision Engine
↓
Qwen3-8B Reasoning
↓
Overlay + TTS

---

# 4. Perception Layer（感知层）

## YOLO标签体系

### 英雄

- 绿色血条英雄（玩家）
- 蓝色血条英雄（队友）
- 红色血条英雄（敌人）

### 小地图

- 小地图
- 小地图视野框
- 队友英雄头像
- 敌方英雄头像

### 兵线

- 蓝色小兵
- 红色小兵
- 蓝色炮车
- 红色炮车

### 建筑

- 蓝方防御塔
- 红方防御塔

### 资源

- 元素龙
- 虚空巢虫
- 峡谷先锋
- 纳什男爵

### 玩家信息

- KDA
- 金币
- 装备
- 用户等级
- 用户状态栏血条

### 技能

- Q
- W
- E
- R
- D
- F

---

# 5. Feature Engine（V2核心）

## 目标

将检测框转换成高价值游戏特征。

---

## Hero Features

输出：

- ally_count
- enemy_count
- ally_hp_avg
- enemy_hp_avg
- ally_hp_total
- enemy_hp_total

新增：

teamfight_power

计算依据：

- 人数
- 血量
- 等级
- 装备

---

## Economy Features

来源：

- 金币
- 等级
- KDA
- 装备

输出：

- player_power
- item_score
- gold_score
- level_score

---

## Skill Features

输出：

- ult_ready
- flash_ready
- ignite_ready
- combat_ready

---

## Wave Features

来源：

- 小兵
- 炮车

输出：

- wave_strength
- wave_direction
- lane_pressure

---

## Objective Features

输出：

- dragon_alive
- herald_alive
- baron_alive
- grub_alive

新增：

objective_priority

---

## Map Features

输出：

- enemy_top
- enemy_mid
- enemy_bot
- enemy_missing

新增：

enemy_heatmap

统计最近60秒敌方活动区域。

---

# 6. Memory Layer

## Hero Memory

记录：

- 最后出现位置
- 最后出现时间
- 行动轨迹

输出：

enemy_jg_missing_time

---

## Objective Memory

记录：

- 龙刷新
- 先锋刷新
- 男爵刷新

---

## Fight Memory

记录：

- 最近团战
- 最近死亡
- 最近资源争夺

---

# 7. Game Understanding Engine

## Phase Engine

Early:
0-14分钟

Mid:
14-25分钟

Late:
25分钟以后

---

## Activity Engine

输出：

- LANING
- ROAMING
- SKIRMISH
- TEAMFIGHT
- OBJECTIVE
- RESET

---

## Context Engine

输出：

- SAFE_FARM
- PRESSURE
- SIEGE
- DEFENSE
- CONTEST
- COLLAPSE
- RETREAT

---

## Combat Engine

输出：

- ADVANTAGE
- EVEN
- DISADVANTAGE

---

## Threat Engine

输出：

- LOW
- MEDIUM
- HIGH

---

# 8. Goal Engine（新增重点）

## 目标

决定当前最优战略目标。

输出：

- CONTEST_DRAGON
- CONTEST_BARON
- CONTEST_HERALD
- PUSH_TOWER
- DEFEND_TOWER
- SPLIT_PUSH
- GROUP
- RETREAT
- RESET

示例：

Goal = CONTEST_DRAGON

---

# 9. Decision Engine V2

输入：

- Feature
- Memory
- State
- Goal

输出：

候选动作列表。

示例：

1. Contest Dragon (95)
2. Push Mid (65)
3. Recall (20)

---

## Rule分类

### Strategic Rules

- 资源优先级
- 推塔优先级
- 防守优先级

### Tactical Rules

- 接团
- 开龙
- 反打
- 撤退

### Risk Rules

- 打野失踪
- 多人消失
- 包夹风险

---

# 10. Qwen3-8B Reasoning Layer

## 定位

LLM作为推理层。

不参与检测。

不参与训练。

直接进行本地推理。

---

输入：

- 当前状态
- 当前目标
- 候选动作

输出：

自然语言建议。

示例：

当前小龙团我方占优。

建议先控制河道视野。

确认敌方打野位置后开龙。

---

# 11. Overlay设计

显示：

Phase

Activity

Context

Goal

Combat

Threat

Top Advice

示例：

Phase: Mid

Goal: Contest Dragon

Threat: Medium

Advice:
控制河道视野后开龙

---

# 12. TTS设计

仅播报高优先级事件。

包括：

- 小龙刷新
- 男爵刷新
- 打野失踪
- 敌方多人消失
- 龙坑集结
- 高风险带线

---

# 13. 开发路线图

## P1（必须）

Feature Engine

Goal Engine

预期收益最大。

---

## P2

Decision Engine V2

从规则驱动升级为目标驱动。

---

## P3

Qwen3-8B

实现智能解释和建议。

---

## P4

Memory V2

增强连续局势理解。

---

## P5

Transformer

仅在拥有大量时序数据后考虑。

当前优先级最低。

---

# 14. 项目最终目标

V1：

规则型游戏助手

V1.5：

具备局势分析能力

V2：

具备目标驱动决策能力

V2.5：

具备LLM推理能力

最终：

轻量级 LOL Agent Assistant
