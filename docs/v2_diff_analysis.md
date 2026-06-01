# V2.0 重构差分分析

## 架构对比

### 当前 (V1)
```
YOLO → DetectionSummary → StateParser(minimap+OCR) → GameState
  → TemporalMemory → RuleEngine(20 rules) → Overlay
```

### V2.0 目标
```
YOLO → Feature Engine(6个Feature) → FeatureBundle → Memory Engine
  → GameState Engine(phase×activity×context×combat×threat)
  → Goal Engine → Decision Engine(V2) → Qwen3-8B → Overlay + TTS
```

## 核心差异

### 1. 数据层：dict → 11 个 Schema

| 当前 | V2.0 | 变化 |
|---|---|---|
| GameState（混合字段） | FeatureBundle + GameState + Goal + Decision | 拆分为 4 层 |
| 无 Feature 概念 | HeroFeature / EconomyFeature / SkillFeature / WaveFeature / ObjectiveFeature / MapFeature | **新增 Feature Engine** |
| 无 Goal 概念 | Goal(goal_type + confidence) | **新增 Goal Engine** |
| Warning(text) | Decision(action + score + reason) | 重命名+结构化 |

### 2. GameState 拆分

| 当前 GameState | V2.0 去向 |
|---|---|
| visible_enemies/allies, hp bars | → HeroFeature |
| gold, level, KDA | → EconomyFeature |
| skills | → SkillFeature |
| minions, towers | → WaveFeature |
| dragon/baron/herald | → ObjectiveFeature |
| minimap positions | → MapFeature |
| phase, combat, threat | → GameState（精简版） |
| **context（新维度）** | → GameState.context |

### 3. 新增模块

| 模块 | 职责 | 当前状态 |
|---|---|---|
| **Feature Engine** | 检测结果 → 6个Feature | 不存在（当前 StateParser 直接产出 GameState） |
| **Context Engine** | safe_farm/pressure/siege/defense/contest/collapse/retreat | 不存在（当前只有 activity） |
| **Goal Engine** | GameState → Goal（9种目标） | 不存在（当前只有 Warning） |
| **Qwen3-8B** | 结构化输入 → 自然语言建议 | 不存在 |

### 4. Memory Layer 重构

| 当前 | V2.0 |
|---|---|
| TemporalMemory（混合） | HeroMemory + ObjectiveMemory + FightMemory → MemoryState |
| 无 FightMemory | 新增：最近团战、最近死亡记录 |

### 5. Decision Engine 升级

| 当前 | V2.0 |
|---|---|
| 20条规则 → Warning | 规则 → Decision List（带 score） |
| 无候选排序 | 生成候选动作列表+评分 |
| 无 Goal 输入 | Goal 作为输入驱动决策 |

## 需要新建的文件

| 文件 | 说明 |
|---|---|
| `schemas/hero.py` | HeroFeature |
| `schemas/economy.py` | EconomyFeature |
| `schemas/skill.py` | SkillFeature |
| `schemas/wave.py` | WaveFeature |
| `schemas/objective.py` | ObjectiveFeature |
| `schemas/map.py` | MapFeature |
| `schemas/feature_bundle.py` | FeatureBundle |
| `schemas/memory.py` | MemoryState |
| `schemas/state.py` | GameState V2 |
| `schemas/goal.py` | Goal |
| `schemas/decision.py` | Decision |
| `reasoning/feature_engine.py` | Feature Engine |
| `reasoning/goal_engine.py` | Goal Engine |
| `reasoning/context_engine.py` | Context Engine |

## 需要重写的文件

| 文件 | 变化 |
|---|---|
| `models/game_state.py` | 重写为精简版 GameState（phase×activity×context×combat×threat） |
| `parser/state_parser.py` | 重写为 Feature Engine |
| `reasoning/state_engine.py` | 重写为 Game Understanding Engine（含新增 Context Engine） |
| `reasoning/rule_engine.py` | 重写为 Decision Engine V2（Goal 驱动） |
| `memory/temporal_memory.py` | 重构为 HeroMemory + ObjectiveMemory + FightMemory |
| `overlay/overlay_ui.py` | 更新显示内容（Goal + Context + Advice） |
| `main.py` | 更新调用链 |

## 开发顺序（P1-P5）

### P1（必须）：Feature Engine + Goal Engine
1. 建立 schemas/（11 个 Pydantic 模型）
2. Feature Engine（从 DetectionSummary 提取 6 个 Feature）
3. Goal Engine（从 GameState + Memory 产出 Goal）
4. 更新 GameState 为 V2 结构

### P2：Decision Engine V2
- Goal 驱动的候选动作列表
- 替换现有 20 条规则

### P3：Qwen3-8B
- 本地模型推理
- 结构化输入 → 自然语言输出

### P4：Memory V2
- FightMemory（团战/死亡记录）
- MemoryState 统一管理

### P5：Transformer（优先级最低）
