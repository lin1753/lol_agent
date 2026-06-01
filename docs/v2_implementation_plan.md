# V2.0 重构施行计划

> 每个 Task 完成后：测试通过 → 更新 PROGRESS.md → 汇报给用户批准 → 进入下一 Task

---

## P1：Schema + Feature Engine（数据层重建）

### P1-T1：创建 schemas/ 包基础 + 6 个 Feature Schema

**新建文件：**
- `schemas/__init__.py` — 统一导出所有 Schema
- `schemas/hero.py` — `HeroFeature(BaseModel)`
- `schemas/economy.py` — `EconomyFeature(BaseModel)`
- `schemas/skill.py` — `SkillFeature(BaseModel)`
- `schemas/wave.py` — `WaveFeature(BaseModel)`
- `schemas/objective.py` — `ObjectiveFeature(BaseModel)`
- `schemas/map.py` — `MapFeature(BaseModel)`

**字段定义严格按 `LOL_Agent_DataSchema_V2.0.md`：**

```python
# schemas/hero.py
class HeroFeature(BaseModel):
    ally_count: int = 0
    enemy_count: int = 0
    ally_hp_avg: float = 0.0      # 0~100
    enemy_hp_avg: float = 0.0     # 0~100
    ally_hp_total: float = 0.0    # sum of HP percentages
    enemy_hp_total: float = 0.0
    visible_allies: int = 0       # 仅画面内可见
    visible_enemies: int = 0

# schemas/economy.py
class EconomyFeature(BaseModel):
    player_level: int = 1
    player_gold: int = 0
    item_count: int = 0
    kills: int = 0
    deaths: int = 0
    assists: int = 0

# schemas/skill.py
class SkillFeature(BaseModel):
    q_ready: bool = False
    w_ready: bool = False
    e_ready: bool = False
    r_ready: bool = False
    d_ready: bool = False
    f_ready: bool = False

# schemas/wave.py
class WaveFeature(BaseModel):
    ally_minions: int = 0
    enemy_minions: int = 0
    ally_cannons: int = 0
    enemy_cannons: int = 0

# schemas/objective.py
class ObjectiveFeature(BaseModel):
    dragon_alive: bool = False
    grub_alive: bool = False
    herald_alive: bool = False
    baron_alive: bool = False

# schemas/map.py
class MapFeature(BaseModel):
    enemy_top: int = 0
    enemy_mid: int = 0
    enemy_bot: int = 0
    enemy_missing: int = 0
```

**测试：** `tests/test_schemas.py` — 每个 Schema 的构造、默认值、JSON 序列化/反序列化

**验收标准：** 6 个 Schema 可独立导入、构造、序列化；`python -m pytest tests/test_schemas.py -v` 全部通过

---

### P1-T2：创建 FeatureBundle + GameState V2 + Goal + Decision Schema

**新建文件：**
- `schemas/feature_bundle.py` — `FeatureBundle(BaseModel)` 组合 6 个 Feature
- `schemas/state.py` — `GameStateV2(BaseModel)` 精简版（5 维：phase × activity × context × combat × threat）
- `schemas/goal.py` — `Goal(BaseModel)` (goal_type + confidence)
- `schemas/decision.py` — `Decision(BaseModel)` (action + score + reason)

```python
# schemas/feature_bundle.py
class FeatureBundle(BaseModel):
    hero: HeroFeature
    economy: EconomyFeature
    skill: SkillFeature
    wave: WaveFeature
    objective: ObjectiveFeature
    map: MapFeature

# schemas/state.py
class GameStateV2(BaseModel):
    game_time: float = 0.0
    phase: str = "early"           # early / mid / late
    activity: str = "laning"       # laning / roaming / skirmish / teamfight / objective / reset
    context: str = "safe_farm"     # safe_farm / pressure / siege / defense / contest / collapse / retreat
    combat: str = "even"           # advantage / even / disadvantage
    threat: str = "low"            # low / medium / high
    # 保留 Objective timers
    dragon_spawn_in: float = -1.0
    baron_spawn_in: float = -1.0
    herald_spawn_in: float = -1.0

# schemas/goal.py
class Goal(BaseModel):
    goal_type: str = "reset"       # 9 种：contest_dragon/baron/herald, push/defend_tower, split_push, group, retreat, reset
    confidence: float = 0.0        # 0~1

# schemas/decision.py
class Decision(BaseModel):
    action: str = ""
    score: float = 0.0
    reason: str = ""
```

**设计决策：** GameState V2 与 V1 GameState **并行存在**。V2 先用于新模块，main.py 在后续 Task 切换时再迁移。

**测试：** 扩展 `tests/test_schemas.py`，覆盖 FeatureBundle 组合、GameStateV2 枚举值、Goal/Decision 序列化

**验收标准：** 11 个 Schema 全部可独立构造和序列化；测试全过

---

### P1-T3：创建 Feature Engine（6 个 Feature 提取器）

**新建文件：**
- `reasoning/feature_engine.py` — `FeatureEngine` 类

**职责：** `DetectionSummary` + OCR 结果 + Minimap 数据 → `FeatureBundle`

```python
class FeatureEngine:
    def extract(self, det_summary: DetectionSummary, ocr_results: dict,
                minimap_detections: list[MinimapDetection],
                frame_shape: tuple[int, int]) -> FeatureBundle:
        hero = self._extract_hero(det_summary)
        economy = self._extract_economy(det_summary, ocr_results)
        skill = self._extract_skill(det_summary)
        wave = self._extract_wave(det_summary)
        objective = self._extract_objective(det_summary)
        map_ = self._extract_map(minimap_detections)
        return FeatureBundle(hero=hero, economy=economy, skill=skill,
                             wave=wave, objective=objective, map=map_)
```

**6 个内部提取器映射（从现有代码迁移逻辑）：**

| 提取器 | 数据来源 | 关键逻辑 |
|---|---|---|
| `_extract_hero` | `det_summary.ally_hp_bars/enemy_hp_bars` | 计数 + 平均 HP + 总 HP |
| `_extract_economy` | `ocr_results['kda/gold/level']` | 解析 KDA/gold/level |
| `_extract_skill` | `det_summary.skills` | 检测到的 skill → ready=True |
| `_extract_wave` | `det_summary.red/blue_minions` | 直接计数 |
| `_extract_objective` | `det_summary.objectives` | 映射 alive 状态 |
| `_extract_map` | `minimap_detections` | 按 Y 坐标分 top/mid/bot + missing |

**测试：** `tests/test_feature_engine.py` — 构造 mock DetectionSummary，验证每个 Feature 的输出

**验收标准：** FeatureEngine 可从真实 DetectionSummary 产出完整 FeatureBundle；测试全过

---

### P1-T4：GameState V2 适配 + main.py 切换入口

**修改文件：**
- `main.py` — 添加 `--v2` 命令行参数，使用 FeatureEngine 替代 StateParser 的路径
- 保持 V1 路径不变（无 `--v2` 参数时走原流程）

**V2 调用链（main.py 中新增）：**
```
YOLO detections → summarize_detections() → DetectionSummary
    → FeatureEngine.extract() → FeatureBundle
    → (后续 P2 Goal Engine, P3 Decision Engine)
    → Overlay 显示
```

**此 Task 不修改 StateParser、StateEngine、RuleEngine、TemporalMemory** — 保持 V1 完整可运行。

**测试：** 更新 `tests/test_main.py`，验证 `--v2` 参数可用且不影响 V1 流程

**验收标准：** `python main.py --v2 --model xxx --video xxx` 可启动并输出 FeatureBundle 信息；`python -m pytest tests/ -v --ignore=tests/test_ocr.py` 全量通过（V1 不受影响）

---

## P2：Goal Engine + Decision Engine V2（决策层升级）

### P2-T1：Context Engine（新增模块）

**新建文件：**
- `reasoning/context_engine.py` — `ContextEngine` 类

**职责：** `FeatureBundle` + `GameStateV2` → context 字段（7 种）

```python
CONTEXT_TYPES = ["safe_farm", "pressure", "siege", "defense",
                 "contest", "collapse", "retreat"]

class ContextEngine:
    def compute(self, features: FeatureBundle, state: GameStateV2,
                memory: TemporalMemory) -> str:
        # 规则：
        # retreat: threat=high + combat=disadvantage
        # collapse: enemy 3+ 推线到高地
        # contest: objective 即将刷新 + 双方接近
        # siege: 我方多人在敌方塔下
        # defense: 敌方多人在我方塔下
        # pressure: 兵线优势 + 敌方缺失
        # safe_farm: 默认
```

**测试：** `tests/test_context_engine.py`

**验收标准：** 7 种 context 都有对应测试用例；全过

---

### P2-T2：Goal Engine

**新建文件：**
- `reasoning/goal_engine.py` — `GoalEngine` 类

**职责：** `GameStateV2` + `FeatureBundle` + `MemoryState` → `Goal`

```python
class GoalEngine:
    def determine(self, state: GameStateV2, features: FeatureBundle,
                  memory: TemporalMemory) -> Goal:
        # 9 种目标，每种有优先级评分：
        # contest_dragon: dragon 即将刷新 + 我方优势
        # contest_baron: baron 即将刷新 + 我方优势
        # contest_herald: herald 在窗口期
        # push_tower: 兵线推进 + 敌方缺失
        # defend_tower: 敌方推线 + 塔下
        # split_push: 后期 + 侧面压力
        # group: 团战阶段 + 人数优势
        # retreat: 威胁高 + 劣势
        # reset: 回城补给
```

**测试：** `tests/test_goal_engine.py` — 每种 goal 触发条件

**验收标准：** 9 种 goal_type 都可正确触发；全过

---

### P2-T3：Decision Engine V2（Goal 驱动 + 候选动作排序）

**新建文件：**
- `reasoning/decision_engine_v2.py` — `DecisionEngineV2` 类

**职责：** `GameStateV2` + `Goal` + `FeatureBundle` + `TemporalMemory` → `list[Decision]`

```python
class DecisionEngineV2:
    def evaluate(self, state: GameStateV2, goal: Goal,
                 features: FeatureBundle, memory: TemporalMemory) -> list[Decision]:
        # 1. 根据 goal_type 选择相关规则集
        # 2. 每条规则产出一个 Decision(action, score, reason)
        # 3. 按 score 降序排列
        # 4. 返回 top-N 候选动作
```

**与 V1 RuleEngine 的区别：**
- V1: 20 条规则全部执行 → Warning 列表
- V2: Goal 驱动 → 只执行相关规则 → Decision 列表（带评分排序）

**设计决策：** DecisionEngineV2 与 RuleEngine **并行存在**。V2 模块只在 `--v2` 模式下调用。

**测试：** `tests/test_decision_engine_v2.py` — 不同 goal 下的候选动作验证

**验收标准：** Decision 列表带评分且排序正确；测试全过

---

### P2-T4：main.py V2 路径集成（P2 完整链路）

**修改文件：**
- `main.py` — `--v2` 模式下串联 FeatureEngine → ContextEngine → GoalEngine → DecisionEngineV2

**V2 完整调用链：**
```
YOLO → DetectionSummary → FeatureEngine → FeatureBundle
    → ContextEngine → context
    → GameStateV2 (phase + activity + context + combat + threat)
    → GoalEngine → Goal
    → DecisionEngineV2 → list[Decision]
    → Overlay (显示 Goal + Top Decision + Context)
    → TTS (播报高优先级 Decision)
```

**修改 overlay/overlay_ui.py：** 新增 `_paint_v2_state()` 方法显示 V2 信息（Goal、Context、Top Decision）

**测试：** 更新 `tests/test_main.py` 验证 V2 全链路；全量回归

**验收标准：** `python main.py --v2 --model xxx --video xxx` 完整运行；Overlay 显示 V2 信息；全量测试通过

---

## P3：Qwen3-8B 推理层（LLM 增强）

### P3-T1：Qwen3-8B 引擎封装

**新建文件：**
- `reasoning/llm_engine.py` — `LlmEngine` 类

**职责：** 结构化 GameStateV2 + Goal + list[Decision] → 自然语言建议

```python
class LlmEngine:
    def __init__(self, model_path: str = "Qwen/Qwen3-8B"):
        # 加载本地模型（vLLM / transformers）

    def advise(self, state: GameStateV2, goal: Goal,
               decisions: list[Decision]) -> str:
        # 构造 prompt：
        #   system: "你是 LOL 战术助手..."
        #   user: JSON 结构化输入
        #   output: 自然语言中文建议（2-3 句）
```

**测试：** `tests/test_llm_engine.py` — mock LLM 验证 prompt 构造和输出解析

**验收标准：** prompt 模板正确、输出格式可控、异常处理完善

---

### P3-T2：main.py 集成 LLM 推理层

**修改文件：**
- `main.py` — `--v2 --llm` 模式下加入 LlmEngine

**调用链追加：**
```
DecisionEngineV2 → list[Decision]
    → LlmEngine.advise() → 自然语言建议
    → Overlay 显示 Advice 文本
    → TTS 播报建议
```

**测试：** 更新集成测试

**验收标准：** LLM 建议可正确显示在 Overlay；无 LLM 环境时 graceful fallback

---

## P4：Memory V2（记忆层重构）

### P4-T1：拆分 Memory 为 3 个子模块

**新建文件：**
- `memory/hero_memory.py` — `HeroMemoryV2`（从 TemporalMemory 提取 hero 部分）
- `memory/objective_memory.py` — `ObjectiveMemory`（龙/男爵/先锋 计时记录）
- `memory/fight_memory.py` — `FightMemory`（团战/死亡记录）

**修改文件：**
- `schemas/memory.py` — `MemoryState(BaseModel)` 组合 3 个子记忆

```python
# memory/hero_memory.py
class HeroMemoryV2:
    def update_hero(self, hero_name, team, position, time): ...
    def get_missing_enemies(self) -> list[dict]: ...
    def get_jungler_missing_duration(self) -> float: ...

# memory/objective_memory.py
class ObjectiveMemory:
    def record_kill(self, objective_type, time): ...
    def get_spawn_timers(self, current_time) -> dict: ...

# memory/fight_memory.py
class FightMemory:
    def record_fight(self, time, result, participants): ...
    def record_death(self, time, killer): ...
    def get_recent_fights(self, n=5) -> list: ...
```

**设计决策：** 新 Memory 与 TemporalMemory **并行存在**。V2 模式使用新 Memory，V1 不受影响。

**测试：** `tests/test_memory_v2.py` — 每个子模块独立测试

**验收标准：** 3 个子模块独立工作；MemoryState 可组合；全量测试通过

---

### P4-T2：main.py V2 Memory 集成 + 全量回归

**修改文件：**
- `main.py` — `--v2` 模式使用 MemoryV2 替代 TemporalMemory

**最终 V2 完整调用链：**
```
YOLO → DetectionSummary → FeatureEngine → FeatureBundle
    → HeroMemoryV2 + ObjectiveMemory + FightMemory → MemoryState
    → ContextEngine → context
    → GameStateV2
    → GoalEngine → Goal
    → DecisionEngineV2 → list[Decision]
    → LlmEngine → 自然语言建议
    → Overlay + TTS
```

**测试：** 全量回归测试（确保 V1 + V2 路径都正常）

**验收标准：** `python -m pytest tests/ -v --ignore=tests/test_ocr.py` 全部通过；V1/V2 路径独立可运行

---

## 总结

| Phase | Tasks | 新建文件 | 修改文件 | 预期产出 |
|---|---|---|---|---|
| **P1** | T1-T4 | 13 个（schemas/ 11 + feature_engine + __init__） | main.py | 11 个 Schema + FeatureEngine + `--v2` 入口 |
| **P2** | T1-T4 | 3 个（context/goal/decision_engine_v2） | main.py, overlay_ui.py | ContextEngine + GoalEngine + DecisionEngineV2 |
| **P3** | T1-T2 | 1 个（llm_engine） | main.py | Qwen3-8B 推理层 |
| **P4** | T1-T2 | 4 个（hero/objective/fight_memory + schemas/memory） | main.py | Memory V2 三模块 |

**关键约束：**
1. 每个 Task 完成后必须 `python -m pytest tests/ -v --ignore=tests/test_ocr.py` 全量通过
2. V1 路径在整个重构过程中保持完整可用
3. V2 模块通过 `--v2` 命令行参数切换
4. 每个 Task 完成后更新 PROGRESS.md 并汇报批准
