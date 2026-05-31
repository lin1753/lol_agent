# LOL Agent Assistant（轻量级复刻版游戏助手）

> 基于 YOLOv8 + State Understanding Engine + Decision Engine 实现的 LOL 智能游戏助手
>
> 目标参考：王者荣耀内置游戏助手 / 腾讯游戏对局助手
>
> 开发环境：RTX4060 Laptop + Python + YOLOv8 + OpenCV

---

# 一、项目目标

本项目目标并非实现职业级 AI（AlphaStar/OpenAI Five），而是实现一个具备：

- 实时局势理解
- 危险预警
- 资源争夺提醒
- 战术建议
- Overlay悬浮窗展示
- TTS语音播报

能力的轻量级 LOL Agent Assistant。

最终效果类似：

```text
━━━━━━━━━━━━━━
LOL Agent
━━━━━━━━━━━━━━

当前阶段：
中期

当前状态：
小龙团

战斗评估：
优势

威胁等级：
中

建议：

✓ 控制小龙视野

✓ 可以接团

⚠ 敌方打野消失28秒

⚠ 下路兵线推进
━━━━━━━━━━━━━━
```

---

# 二、项目整体架构

```text
Screen Capture
       │
       ▼
YOLO Detector
       │
       ▼
State Understanding Engine
       │
       ▼
Decision Engine
       │
       ▼
Overlay + TTS
```

系统逻辑：

```text
检测
 ↓
状态理解
 ↓
局势判断
 ↓
战术建议
 ↓
用户提示
```

---

# 三、现有数据资源

## 1. 原始截图

```text
719张
1920×1080
```

用途：

- YOLO训练
- 状态分析

---

## 2. XML标注

包含：

### 英雄

```text
绿色血条英雄（玩家）
蓝色血条英雄（队友）
红色血条英雄（敌方）
```

### 兵线

```text
蓝色小兵
红色小兵

蓝色炮车
红色炮车
```

### 建筑

```text
蓝方防御塔
红方防御塔
```

### 中立资源

```text
元素龙
峡谷先锋
虚空巢虫
纳什男爵
```

### UI信息

```text
游戏时间
KDA
金币
等级

Q技能
W技能
E技能
R技能
D技能
F技能

用户状态栏血条
```

---

## 3. 05 文件

用途：

```text
当前主视野英雄语义验证
```

示例：

```json
{
  "我方": ["菲兹"],
  "敌方": []
}
```

---

## 4. 06 文件

用途：

```text
小地图英雄语义验证
```

---

## 5. minimap_labels_v2

用途：

```text
小地图空间关系分析
```

用于：

- 敌我位置分析
- 集结判断
- 龙坑区域分析

---

# 四、YOLO模型设计

## 模型选型

推荐：

```text
YOLOv8m
```

原因：

- 数据量较小（719张）
- RTX4060足够运行
- 训练稳定
- 推理速度快

---

## 输入

```text
1920×1080
```

---

## 推荐训练参数

```yaml
model: yolov8m.pt

imgsz: 1280

batch: 4~8

epochs: 100

optimizer: AdamW

cos_lr: True

patience: 20

amp: True
```

---

# 五、State Understanding Engine

这是整个项目最重要的部分。

职责：

```text
识别当前游戏状态
```

而不是：

```text
只识别目标
```

---

# 六、状态体系设计

最终统一输出：

```json
{
  "phase": "mid_game",
  "context": "dragon_fight",
  "combat": "advantage",
  "lane": "pushing",
  "objective": "dragon",
  "threat": "medium"
}
```

---

# 七、Game Phase（游戏阶段）

## Early Game

```text
0~14分钟
```

关注：

- 对线
- 巢虫
- 第一条龙

---

## Mid Game

```text
14~25分钟
```

关注：

- 先锋
- 一塔
- 二塔
- 小龙团

---

## Late Game

```text
25分钟+
```

关注：

- 男爵
- 龙魂
- 高地

---

输出：

```json
{
  "phase":"mid_game"
}
```

---

# 八、Context Engine（场景识别）

核心问题：

```text
当前在干什么？
```

---

## 对线（Laning）

条件：

```text
我方1~2人

敌方1~2人
```

输出：

```json
{
  "context":"laning"
}
```

---

## 双人路对线

条件：

```text
玩家

1个队友

1~3个敌人
```

输出：

```json
{
  "context":"duo_laning"
}
```

---

## 带线（Split Push）

条件：

```text
玩家独自出现

附近无队友

附近无敌人
```

输出：

```json
{
  "context":"split_push"
}
```

---

## 遭遇战（Skirmish）

条件：

```text
双方2~4人
```

输出：

```json
{
  "context":"skirmish"
}
```

---

## 团战（Teamfight）

条件：

```text
双方≥3人

且距离聚集
```

输出：

```json
{
  "context":"teamfight"
}
```

---

## 小龙团

条件：

```text
元素龙存在

双方靠近龙坑
```

输出：

```json
{
  "context":"dragon_fight"
}
```

---

## 男爵团

条件：

```text
男爵存在

双方靠近大龙区
```

输出：

```json
{
  "context":"baron_fight"
}
```

---

# 九、Combat State（战斗态势）

评估：

```text
人数

等级

血量
```

---

计算：

```python
combat_score =
人数评分
+等级评分
+血量评分
```

---

输出：

### 优势

```json
{
 "combat":"advantage"
}
```

### 均势

```json
{
 "combat":"even"
}
```

### 劣势

```json
{
 "combat":"disadvantage"
}
```

---

# 十、Lane State（兵线态势）

利用：

```text
小兵

炮车

防御塔
```

分析：

---

## 推线

```json
{
 "lane":"pushing"
}
```

---

## 被推

```json
{
 "lane":"being_pushed"
}
```

---

## 均势

```json
{
 "lane":"neutral"
}
```

---

# 十一、Objective State（资源状态）

统一管理：

```text
元素龙

峡谷先锋

虚空巢虫

纳什男爵
```

---

输出：

```json
{
 "dragon_alive":true,

 "dragon_spawn_in":45,

 "baron_alive":false,

 "herald_alive":true
}
```

---

# 十二、Threat State（威胁分析）

## Low

```text
敌方位置清晰
```

---

## Medium

```text
2人失踪
```

---

## High

```text
打野失踪

多人失踪
```

---

输出：

```json
{
 "threat":"high"
}
```

---

# 十三、Decision Engine

输入：

```json
GameState
```

输出：

```text
建议
```

---

# 一级提醒

## 打野消失

```text
敌方打野消失25秒
```

---

## 多人消失

```text
敌方3人消失
```

---

## 龙刷新

```text
小龙30秒刷新
```

---

## 男爵刷新

```text
男爵60秒刷新
```

---

# 二级建议

## 对线优势

```text
建议积极换血
```

---

## 对线劣势

```text
建议稳健补刀
```

---

## 小龙团优势

```text
建议争夺小龙
```

---

## 小龙团劣势

```text
建议放龙换资源
```

---

## 高风险带线

```text
敌方多人消失

建议后撤
```

---

## 防御塔压力

```text
下路兵线进塔

建议回防
```

---

# 十四、V1规则池

建议先实现20条规则。

---

## Threat Rules

```text
打野消失

多人消失

带线风险

包夹风险
```

---

## Objective Rules

```text
龙刷新

先锋刷新

男爵刷新

龙团提醒

男爵团提醒
```

---

## Combat Rules

```text
优势接团

劣势撤退

收割机会
```

---

## Lane Rules

```text
推线

被推

塔压
```

---

## Economy Rules

```text
等级领先

等级落后

金币领先

金币落后
```

---

# 十五、Overlay设计

技术：

```text
PyQt5
```

显示：

```text
阶段

状态

威胁等级

建议列表
```

---

# 十六、语音系统

技术：

```text
pyttsx3
```

仅播报：

```text
高危事件

资源刷新

团战预警
```

避免频繁播报。

---

# 十七、未来升级路线

## V1

```text
YOLO
+
State Understanding Engine
+
Decision Engine
```

目标：

实现类似王者荣耀助手的核心功能。

---

## V2

增加：

```text
Temporal Memory
```

实现：

```text
敌方行为记忆

Gank概率分析

控龙概率分析
```

---

## V3

增加：

```text
Temporal Transformer
```

实现：

```text
行为预测

团战预测

资源争夺预测
```

---

## V4

增加：

```text
Qwen3-8B
```

仅负责：

```text
自然语言解释
```

例如：

为什么建议撤退？

↓

因为敌方中野失踪且我方人数不足。
```

---

# 十八、项目简历描述（推荐）

## 项目名称

LOL Agent Assistant

---

## 技术栈

```text
Python

YOLOv8

OpenCV

PyQt5

PyTorch

Temporal Memory

Rule-Based Tactical Engine
```

---

## 项目描述

```text
基于YOLOv8构建LOL实时游戏助手。

实现游戏目标检测、局势理解、
资源争夺分析、危险预警和战术建议。

设计State Understanding Engine、
Decision Engine与Overlay交互系统，
实现类似王者荣耀游戏助手的实时辅助能力。
```

---

# 最终结论

当前阶段最优方案：

```text
YOLOv8m
+
State Understanding Engine
+
Decision Engine
+
Overlay
+
TTS
```

先把“状态理解”和“战术决策”做到稳定可靠，再逐步引入 Temporal Memory、Transformer 和 Qwen3-8B 作为增强模块。

这是在你现有数据、硬件和开发周期下，成功率最高且最接近商业游戏助手产品形态的实现路线。