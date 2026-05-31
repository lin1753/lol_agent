# 优化 v3 方案

## 1. combat_state 基于 HP Bar 计算

**现状**：combat_state 基于人数 + OCR 玩家血量（不准确，player_level 已屏蔽）

**优化**：利用 YOLO 检测到的英雄血条计算实际血量对比

YOLO 29类已检测：
- `green_hp_hero` / `blue_hp_hero` → 友方英雄（绿/蓝血条）
- `red_hp_hero` → 敌方英雄（红血条）
- `green_hp_bar` / `blue_hp_bar` / `red_hp_bar` → HP bar UI 元素（可推算血量百分比）

**计算逻辑**：
```python
# 友方血条总宽度 vs 敌方血条总宽度 → 血量对比
ally_hp_ratio = sum(ally_bar_widths) / max_ally_bar_width
enemy_hp_ratio = sum(enemy_bar_widths) / max_enemy_bar_width
combat_score = numbers_advantage * 0.3 + hp_advantage * 0.5 + missing_penalty * 0.2
```

**修改文件**：
- `reasoning/state_engine.py`: `compute_combat_state()` 使用血条数据

---

## 2. 加入 LLM 推理层

**现状**：规则引擎 → 固定文本模板（如 "敌方打野已消失 X 秒"）

**优化**：加入 LLM 作为语言理解层

**架构**：
```
State Engine（结构化状态）
    ↓
Decision Engine（规则判断 + LLM 建议）
    ↓
  ┌─ 规则层：生成结构化告警（保留，快速）
  └─ LLM 层：基于状态生成自然语言战术建议（新增）
    ↓
Overlay + Voice
```

**LLM 输入**（结构化 prompt）：
```json
{
  "game_phase": "mid_game",
  "activity": "laning",
  "combat": "advantage",
  "threat": "medium",
  "time": "14:30",
  "kda": "5/2/8",
  "gold": 12000,
  "missing_enemies": 2,
  "jungler_missing_seconds": 25,
  "dragon_spawn_in": 45,
  "dragon_alive": true,
  "lane_state": "pushing"
}
```

**LLM 输出**：
```
你目前在中路对线，经济领先。敌方打野已消失25秒，可能来gank。
小龙即将刷新，建议提前布置河道视野。当前兵线推进中，
可考虑配合打野拿龙。
```

**技术选型**：
- 本地部署：Qwen3-8B（已计划在 V4 路线）
- 或 API 方案：先用 GPT-4o API 验证效果，再迁移到本地
- 或轻量化：用小模型（Qwen3-1.8B）做推理

**触发方式**：
- 不是每帧调用（太慢）
- 每 10-15 秒调用一次（或状态发生重大变化时）
- 异步调用，不阻塞主循环

**修改文件**：
- `reasoning/llm_engine.py`（新文件）：LLM 推理层
- `reasoning/rule_engine.py`: 集成 LLM 输出
- `main.py`: 异步调用 LLM

---

## 优先级

1. **先做 HP bar 血量对比**（纯代码改动，快速验证）
2. **再做 LLM 推理层**（需要选择模型/ API）
