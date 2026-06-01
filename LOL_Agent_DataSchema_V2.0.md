LOL Agent DataSchema V2.0
文档定位

本文档定义 LOL Agent 全系统统一数据规范（Data Schema）。

目标：

YOLO
↓
Feature Engine
↓
GameState Engine
↓
Goal Engine
↓
Decision Engine
↓
Qwen3-8B

所有模块共享统一的数据结构。

一、设计原则
原则1：统一字段命名

禁止出现：

enemy_num

enemy_count

enemy_cnt

同时存在。

统一：

enemy_count
原则2：统一Schema

所有模块输入输出必须基于 Schema。

禁止：

dict

到处乱传。

原则3：JSON作为交换格式

内部：

Pydantic

模块通信：

JSON
二、项目目录结构
lol_agent/

schemas/

├── hero.py
├── economy.py
├── skill.py
├── wave.py
├── objective.py
├── map.py
├── feature_bundle.py
├── memory.py
├── state.py
├── goal.py
└── decision.py
三、Feature Layer

Feature Layer负责：

检测结果
↓
高价值游戏特征
3.1 HeroFeature
来源

YOLO：

绿色血条英雄

蓝色血条英雄

红色血条英雄
Schema
class HeroFeature(BaseModel):

    ally_count: int

    enemy_count: int

    ally_hp_avg: float

    enemy_hp_avg: float

    ally_hp_total: float

    enemy_hp_total: float

    visible_allies: int

    visible_enemies: int
衍生特征
Teamfight Power

计算：

teamfight_power =
人数
+
血量
+
等级
+
装备

输出：

teamfight_power: float

范围：

0~1
3.2 EconomyFeature
来源
金币

等级

装备

KDA
Schema
class EconomyFeature(BaseModel):

    player_level: int

    player_gold: int

    item_count: int

    kills: int

    deaths: int

    assists: int
衍生特征
power_score

gold_score

level_score
3.3 SkillFeature
来源
Q
W
E
R

D
F
Schema
class SkillFeature(BaseModel):

    q_ready: bool

    w_ready: bool

    e_ready: bool

    r_ready: bool

    d_ready: bool

    f_ready: bool
衍生特征
ult_ready

flash_ready

combat_ready
3.4 WaveFeature
来源
蓝色小兵

红色小兵

蓝色炮车

红色炮车
Schema
class WaveFeature(BaseModel):

    ally_minions: int

    enemy_minions: int

    ally_cannons: int

    enemy_cannons: int
衍生特征
Wave Strength
wave_strength
Wave Direction
push

neutral

being_pushed
Lane Pressure
low

medium

high
3.5 ObjectiveFeature
来源
元素龙

巢虫

峡谷先锋

男爵
Schema
class ObjectiveFeature(BaseModel):

    dragon_alive: bool

    grub_alive: bool

    herald_alive: bool

    baron_alive: bool
衍生特征
objective_priority

范围：

0~1
3.6 MapFeature
来源
小地图

队友头像

敌方头像
Schema
class MapFeature(BaseModel):

    enemy_top: int

    enemy_mid: int

    enemy_bot: int

    enemy_missing: int
衍生特征
Enemy Heatmap

统计：

最近60秒
敌方活动区域

输出：

enemy_heatmap
四、FeatureBundle

统一Feature输出。

Schema
class FeatureBundle(BaseModel):

    hero: HeroFeature

    economy: EconomyFeature

    skill: SkillFeature

    wave: WaveFeature

    objective: ObjectiveFeature

    map: MapFeature
五、Memory Layer
5.1 Hero Memory
Schema
class HeroMemory(BaseModel):

    hero_id: str

    last_seen_position: str

    last_seen_time: float
输出
enemy_jg_missing_time
5.2 Objective Memory
Schema
class ObjectiveMemory(BaseModel):

    dragon_spawn_time: float

    herald_spawn_time: float

    baron_spawn_time: float
5.3 Fight Memory
Schema
class FightMemory(BaseModel):

    recent_fights: list

    recent_deaths: list
5.4 MemoryState
class MemoryState(BaseModel):

    hero_memory

    objective_memory

    fight_memory
六、GameState Layer

这是系统最重要的数据结构。

Schema
class GameState(BaseModel):

    phase: str

    activity: str

    context: str

    combat: str

    threat: str
6.1 Phase
early

mid

late
6.2 Activity
laning

roaming

skirmish

teamfight

objective

reset
6.3 Context
safe_farm

pressure

siege

defense

contest

collapse

retreat
6.4 Combat
advantage

even

disadvantage
6.5 Threat
low

medium

high
七、Goal Layer

Goal负责：

当前最应该做什么
Schema
class Goal(BaseModel):

    goal_type: str

    confidence: float
Goal Types
contest_dragon

contest_baron

contest_herald

push_tower

defend_tower

split_push

group

retreat

reset
示例
{
  "goal_type":"contest_dragon",
  "confidence":0.91
}
八、Decision Layer
Schema
class Decision(BaseModel):

    action: str

    score: float

    reason: str
示例
{
  "action":"contest_dragon",
  "score":95,
  "reason":"人数优势"
}
九、Qwen输入规范

禁止：

YOLO框
↓
Qwen

必须：

GameState
↓
Goal
↓
Decision
↓
Qwen
标准输入
{
  "state": {},

  "goal": {},

  "decisions": []
}
十、标准数据流
YOLO Detector
↓
Feature Engine
↓
FeatureBundle
↓
Memory Engine
↓
GameState Engine
↓
GameState
↓
Goal Engine
↓
Goal
↓
Decision Engine
↓
Decision List
↓
Qwen3-8B
↓
Advice
↓
Overlay
↓
TTS
十一、开发规范
Rule 1

所有模块必须使用 Schema。

Rule 2

新增字段必须更新 Schema。

Rule 3

禁止模块间传裸 dict。

Rule 4

统一使用：

Pydantic BaseModel
Rule 5

Qwen只接收结构化状态。

十二、最终核心对象
HeroFeature

EconomyFeature

SkillFeature

WaveFeature

ObjectiveFeature

MapFeature

FeatureBundle

MemoryState

GameState

Goal

Decision

这 11 个对象构成整个 LOL Agent 的统一数据协议，是后续 Feature Engine、Goal Engine、Decision Engine 和 Qwen3-8B 推理层开发的基础。