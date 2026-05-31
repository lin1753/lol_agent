# OCR 优化方案

## 问题诊断

OCR 系统在实际运行中存在严重性能和准确性问题：

| 元素 | OCR 耗时 | 准确性 | 问题 |
|---|---|---|---|
| game_time | 35ms | ✅ 准确 | 读到的是过时值，不应依赖 OCR |
| kda | 69ms | ✅ 准确 | 可用 |
| gold | 82ms | ⚠️ 偶尔读为 0 | 可用但需缓存 |
| player_level | **4471ms** | ❌ 不准 | 39x37px 太小，OCR 崩溃 |

**根本原因**: OCR 设计思路错误 — 不应该让 OCR 读取 YOLO 已经能精确定位的信息。

## 优化策略

### 1. game_time: 从视频帧序号计算（不需要 OCR）

```python
# 视频模式：直接从帧序号计算
game_time = frame_index / video_fps  # 精确到毫秒

# 实时游戏模式：从 OCR 读取（每 3 秒一次，不阻塞主循环）
```

### 2. player_level: 完全不识别

- bbox 仅 39x37px，OCR 无法可靠读取
- 在 overlay 中不显示等级（或显示为未知）

### 3. gold + kda: 保留 OCR，限频异步

```python
# 只对 gold 和 kda 做 OCR，每 2 秒一次
if frame_count % 60 == 0:  # 每 2 秒 @30fps
    gold = ocr.recognize_number(gold_crop)
    kda = ocr.recognize_kda(kda_crop)
# 其他帧使用缓存值
```

### 4. YOLO + OCR 互补分工

| 任务 | 方案 | 说明 |
|---|---|---|
| game_time | 视频帧序号计算 | 精确无延迟 |
| kda | OCR（每 2s） | 准确且快 |
| gold | OCR（每 2s） | 准确但需缓存 |
| player_level | 不识别 | bbox 太小不可靠 |
| 英雄检测 | YOLO | ✅ |
| 小兵/塔 | YOLO | ✅ |
| 技能 | YOLO | ✅ |
| minimap | OpenCV | ✅ |

### 5. 实时游戏模式的 game_time 处理

实时游戏无法用帧序号，需要 OCR。但可以：
- 只在 topbar OCR（35ms，很快）
- 不在 HUD OCR（避免 player_level 的 4.5s 延迟）
- 缓存 + 每 3 秒刷新一次

## 修改文件

| 文件 | 修改 |
|---|---|
| `perception/detection_summary.py` | 从 OCR 列表中移除 `player_level` |
| `main.py` | game_time 在视频模式下从帧序号计算；OCR 限频每 2s |
| `perception/ocr_engine.py` | 只对 gold/kda 调用 OCR |

## 预期效果

- **FPS**: 从 ~5 FPS 提升到 ~10+ FPS（去掉 player_level 的 4.5s 延迟）
- **游戏时间**: 精确到帧（视频模式）或 1s 内（实时模式）
- **gold/kda**: 每 2 秒更新一次，足够实时
