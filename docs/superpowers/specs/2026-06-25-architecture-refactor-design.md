# LOL Agent 架构重构 Spec

**日期:** 2026-06-25
**分支:** main
**范围:** Issues #7 #8 #9 #10

## 目标

1. 删除 V1 管线代码，V2 成为唯一管线
2. 提取重复解析函数到共享模块
3. 引入统一配置管理
4. main.py 从 ~591 行瘦身到 ~380 行

## 删除清单

| 文件 | 原因 |
|------|------|
| `reasoning/rule_engine.py` | V1 专属，V2 用 DecisionEngineV2 |
| `reasoning/state_engine.py` | V1 专属，V2 用 ContextEngine |
| `parser/state_parser.py` | V1 专属，_parse_time 移到 utils/parsing |
| `tests/test_rule_engine.py` | V1 测试 |
| `tests/test_state_engine.py` | V1 测试 |
| `tests/test_state_parser.py` | V1 测试 |

**不删除:** `models/game_state.py`（TemporalMemory 依赖）、`memory/temporal_memory.py`（V2 引擎仍 import）

## 新建清单

| 文件 | 内容 |
|------|------|
| `config.py` | AgentConfig dataclass，集中所有阈值/路径/语言 |
| `utils/parsing.py` | parse_kda, parse_int, parse_time 三个共享函数 |
| `tests/test_parsing.py` | 共享解析函数测试 |
| `tests/test_config.py` | Config 默认值测试 |

## 修改清单

| 文件 | 改动 |
|------|------|
| `main.py` | 删 V1 分支，用 AgentConfig，~591→~380 行 |
| `feature_engine.py` | import 改为 from utils.parsing |
| `overlay/overlay_ui.py` | 删除 Warning/WarningLevel import 和 V1 专属方法（update_warnings），保留 V2 渲染 |
| `voice/tts_engine.py` | 删除 Warning/WarningLevel import 和 speak_warnings 方法 |
| `tests/test_feature_engine.py` | 更新 import（如需要） |

## 新建模块设计

### config.py

```python
from dataclasses import dataclass, field
import os

@dataclass
class AgentConfig:
    # Pipeline
    fps_target: float = 5.0
    memory_window: int = 30

    # OCR
    ocr_lang: str = "ch"
    ocr_interval: int = 60
    status_interval: int = 30

    # Model paths
    yolo_model: str | None = None
    llm_model: str | None = None  # fallback: LOL_LLM_MODEL_PATH env

    # Overlay position
    overlay_x: int = 1500
    overlay_y: int = 50
    overlay_width: int = 320

    # FeatureEngine thresholds
    skill_confidence: float = 0.7
    level_max: int = 18

    # Objective timing (2025/2026 season, seconds)
    dragon_first_spawn: int = 300
    dragon_respawn: int = 300
    baron_first_spawn: int = 1500
    baron_respawn: int = 360
    herald_first_spawn: int = 480
    herald_despawn: int = 1170

    @classmethod
    def from_args(cls, args) -> "AgentConfig":
        """Build config from argparse namespace, with env var fallbacks."""
        cfg = cls()
        if args.fps:
            cfg.fps_target = args.fps
        if args.model:
            cfg.yolo_model = args.model
        if args.llm_model:
            cfg.llm_model = args.llm_model
        elif not cfg.llm_model:
            cfg.llm_model = os.environ.get("LOL_LLM_MODEL_PATH")
        return cfg
```

### utils/parsing.py

```python
def parse_kda(kda_str: str) -> tuple[int, int, int]: ...
def parse_int(s: str) -> int: ...
def parse_time(time_str: str) -> float: ...
```

从 state_parser.py 的 _parse_time、state_parser.py 和 feature_engine.py 的 _parse_kda/_parse_int 提取，逻辑不变。

## overlay/tts 清理细节

### overlay/overlay_ui.py
- 删除 `from reasoning.rule_engine import Warning, WarningLevel`
- 删除 V1 OverlayWidget 的 `update_warnings(warnings)` 方法
- 删除 V1 OverlayWidget 的 `update_state(data)` 中 Warning 渲染逻辑
- V2 OverlayWidgetV2 不受影响（已用 Decision 对象渲染）

### voice/tts_engine.py
- 删除 `from reasoning.rule_engine import Warning, WarningLevel`
- 删除 `speak_warnings(warnings)` 方法
- 保留 TTS 基础设施（start/stop），后续可扩展为播报 Decision

## main.py 瘦身策略

1. 删除 `--v2` flag（默认 V2），保留但标记 deprecated（向后兼容）
2. 删除 `if not self._v2:` 整个 V1 分支（约 80 行）
3. 删除 `_display_status`、`_make_state_info`、`_display_warnings` 方法（V1 专属）
4. 初始化用 AgentConfig 替代硬编码
5. `StateParser._parse_time` 调用改为 `from utils.parsing import parse_time`

## 执行顺序

1. 新建 `utils/parsing.py` + `tests/test_parsing.py` → 验证通过
2. 新建 `config.py` + `tests/test_config.py` → 验证通过
3. 修改 `feature_engine.py` import → 运行 test_feature_engine
4. 修改 `overlay/overlay_ui.py` 删除 Warning 相关 → 运行 test_overlay
5. 修改 `voice/tts_engine.py` 删除 Warning 相关 → 运行 test_tts
6. 修改 `main.py` 删 V1 分支、用 Config → 运行 test_main
7. 删除 V1 文件（rule_engine, state_engine, state_parser + tests）
8. 全量测试 → 252+ tests pass
