# 优化方案 v2

## 1. 禁用 player_level OCR
从 `UI_CLASSES` 移除，overlay 不显示等级。

## 2. 中立资源计时器修复
- 仅追踪小龙（下河道）和男筠（上河道）
- 移除先锋/巢虫的独立计时
- 资源状态改由 minimap 识别辅助判断

## 3. game_phase × activity 二维模型
将单一 `context` 拆分为两个独立维度：

| 维度 | 字段 | 取值 |
|---|---|---|
| 宏观阶段 | `game_phase` | early_game / mid_game / late_game |
| 当前活动 | `activity` | laning / roaming / skirmish / teamfight / objective |

判断逻辑：
- **laning**: 玩家附近只有 1-2 个友方，无敌人或只有 1 个敌人
- **roaming**: 玩家不在原线路（从 minimap 位置推断），且附近无敌人
- **skirmish**: 双方 2-4 人，距离较近
- **teamfight**: 双方 ≥3 人聚集
- **objective**: 正在龙坑/男筠坑附近且目标存在

优先级：teamfight > objective > skirmish > roaming > laning（默认）
