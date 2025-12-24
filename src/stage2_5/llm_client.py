# src/stage2_5/llm_client.py
from __future__ import annotations

import json
from typing import Callable, Any, Dict


class LLMClient:
    def __init__(self, call_fn: Callable[[str], str]):
        self.call_fn = call_fn

    def call(self, prompt: str) -> Dict[str, Any]:
        raw = self.call_fn(prompt)

        # If already dict (like your fake llm), accept it
        if isinstance(raw, dict):
            return raw

        if not isinstance(raw, str):
            return {"rejected": True, "reason": "LLM returned non-string, non-dict response"}

        try:
            return json.loads(raw)
        except Exception:
            return {"rejected": True, "reason": "LLM returned non-JSON output"}