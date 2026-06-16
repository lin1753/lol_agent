"""LLM Engine — Qwen3-8B local inference for natural language advice.

Transforms structured GameStateV2 + Goal + Decision list into
Chinese tactical advice via local LLM reasoning.

Only runs when --v2 --llm flags are both set.
"""

from __future__ import annotations

import json
import time
from typing import List, Optional

from schemas.decision import Decision
from schemas.goal import Goal
from schemas.state import GameStateV2


_SYSTEM_PROMPT = """你是 LOL 战术助手。根据游戏状态 JSON，用中文给出 1-2 句战术建议。
规则：
1. 直接给建议，不重复状态
2. 围绕当前目标说
3. 60字以内"""

_USER_TEMPLATE = """游戏状态：
{state_json}

当前目标：{goal_type}（置信度 {confidence}）
首选行动：{action}（{reason}）

给出战术建议："""


class LlmEngine:
    """Local Qwen3-8B inference engine.

    Args:
        model_path: HuggingFace model ID or local path.
        quantize: Use 4-bit quantization (requires bitsandbytes).
        device: Device to load model on.
        max_new_tokens: Max tokens to generate.
        advise_interval: Minimum seconds between LLM calls.
    """

    def __init__(
        self,
        model_path: str = "Qwen/Qwen3-0.6B",
        quantize: bool = True,
        device: str = "auto",
        max_new_tokens: int = 150,
        advise_interval: float = 10.0,
    ) -> None:
        self._model_path = model_path
        self._quantize = quantize
        self._device = device
        self._max_new_tokens = max_new_tokens
        self._advise_interval = advise_interval
        self._model = None
        self._tokenizer = None
        self._last_advise_time: float = 0.0
        self._last_goal: str = ""
        self._ready = False

    def start(self) -> bool:
        """Load the model. Returns True on success."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            import torch

            print(f"  LLM: loading {self._model_path}...", flush=True)

            tok_kwargs = {"trust_remote_code": True}
            model_kwargs = {"trust_remote_code": True, "device_map": self._device}

            if self._quantize and "8B" in self._model_path:
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                )
                model_kwargs["quantization_config"] = bnb_config

            self._tokenizer = AutoTokenizer.from_pretrained(
                self._model_path, **tok_kwargs
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self._model_path, **model_kwargs
            )
            self._ready = True
            print(f"  LLM: ready ({self._model_path})", flush=True)
            return True

        except Exception as e:
            print(f"  LLM: failed to load ({type(e).__name__}: {e})", flush=True)
            self._ready = False
            return False

    def should_advise(self, state: GameStateV2, goal: Goal) -> bool:
        """Check if we should generate advice now.

        Triggers on:
        - Goal type change
        - Interval elapsed since last advice
        """
        now = time.time()
        if goal.goal_type != self._last_goal:
            self._last_goal = goal.goal_type
            return True
        if now - self._last_advise_time >= self._advise_interval:
            return True
        return False

    def advise(
        self,
        state: GameStateV2,
        goal: Goal,
        decisions: List[Decision],
    ) -> Optional[str]:
        """Generate natural language advice.

        Args:
            state: Current GameStateV2.
            goal: Current Goal.
            decisions: Ranked Decision list.

        Returns:
            Chinese advice string, or None if LLM unavailable.
        """
        if not self._ready or self._model is None:
            return None

        prompt = self._build_prompt(state, goal, decisions)

        try:
            from transformers import TextStreamer

            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            text = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
                enable_thinking=False,
            )
            inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)

            with __import__("torch").no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=self._max_new_tokens,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                )

            # Decode only the new tokens
            new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
            response = self._tokenizer.decode(new_tokens, skip_special_tokens=True)
            response = response.strip()

            self._last_advise_time = time.time()
            return response if response else None

        except Exception as e:
            print(f"  LLM: inference error ({e})")
            return None

    def stop(self) -> None:
        """Release model resources."""
        self._model = None
        self._tokenizer = None
        self._ready = False

    @staticmethod
    def _build_prompt(
        state: GameStateV2,
        goal: Goal,
        decisions: List[Decision],
    ) -> str:
        """Build the user prompt from structured state."""
        state_dict = {
            "phase": state.phase,
            "activity": state.activity,
            "context": state.context,
            "combat": state.combat,
            "threat": state.threat,
            "game_time": f"{int(state.game_time // 60)}:{int(state.game_time % 60):02d}",
        }
        top = decisions[0] if decisions else None
        return _USER_TEMPLATE.format(
            state_json=json.dumps(state_dict, ensure_ascii=False, indent=2),
            goal_type=goal.goal_type,
            confidence=round(goal.confidence, 2),
            action=top.action if top else "无",
            reason=top.reason if top else "无",
        )
