from __future__ import annotations
import time
import json
import logging
from typing import Any, Dict

import os
from dotenv import load_dotenv

# Load environment variables immediately
load_dotenv()

from openai import OpenAI
from anthropic import Anthropic

from .config_loader import load_settings
from .token_logger import log_usage


class LLMClientRealtime:
    """
    A unified interface for calling OpenAI or Anthropic models
    with retry logic, JSON parsing, and modern API compatibility.

    WORKS WITH:
      • GPT-4.1, GPT-4.1-Mini, GPT-5.1, GPT-5.1-Preview (OpenAI)
      • Claude 3.5, Claude 3.7 (Anthropic)
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        max_retries: int | None = None,
    ):
        # -------------------------------
        # Load API keys
        # -------------------------------
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        if not self.openai_api_key and not self.anthropic_api_key:
            raise RuntimeError(
                "No API keys found. Ensure OPENAI_API_KEY / ANTHROPIC_API_KEY exist in .env"
            )

        # -------------------------------
        # Load YAML settings
        # -------------------------------
        settings = load_settings()
        llm_settings = settings.get("llm", {})

        self.provider = provider or llm_settings.get("provider", "openai")
        self.model = model or llm_settings.get("model", "gpt-4.1-mini")

        self.temperature = (
            temperature if temperature is not None 
            else llm_settings.get("temperature", 0.0)
        )

        # Note: this will map to max_completion_tokens for OpenAI
        self.max_tokens = (
            max_tokens if max_tokens is not None
            else llm_settings.get("max_output_tokens", 2048)
        )

        self.max_retries = (
            max_retries if max_retries is not None 
            else llm_settings.get("retry_limit", 5)
        )

        # -------------------------------
        # Build clients
        # -------------------------------
        self._openai_client = OpenAI(api_key=self.openai_api_key)
        self._anthropic_client: Anthropic | None = None

    # ============================================================
    # OPENAI CALL — Updated for 2025 SDK
    # ============================================================
    def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """
        Modern OpenAI Chat Completions API:
        • Uses max_completion_tokens instead of max_tokens.
        • Usage is a pydantic model.
        """

        response = self._openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_completion_tokens=self.max_tokens,  # ← REQUIRED FIX
        )

        # New SDK: usage is a pydantic object.
        usage_obj = response.usage

        prompt_tokens = getattr(usage_obj, "prompt_tokens", 0)
        completion_tokens = getattr(usage_obj, "completion_tokens", 0)

        # Log API cost
        log_usage(
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            provider="openai"
        )

        return {
            "text": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }
        }

    # ============================================================
    # ANTHROPIC CALL — Updated for Messages API
    # ============================================================
    def _call_anthropic(self, prompt: str) -> Dict[str, Any]:

        if self._anthropic_client is None:
            self._anthropic_client = Anthropic(api_key=self.anthropic_api_key)

        msg = self._anthropic_client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,    # Anthropic STILL uses max_tokens
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        text = msg.content[0].text if msg.content else ""

        usage = getattr(msg, "usage", None)
        if usage:
            prompt_tokens = getattr(usage, "input_tokens", 0)
            completion_tokens = getattr(usage, "output_tokens", 0)
        else:
            prompt_tokens = completion_tokens = 0

        log_usage(
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            provider="anthropic"
        )

        return {
            "text": text,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }
        }

    # ============================================================
    # PUBLIC: RAW TEXT CALL
    # ============================================================
    def call_text(self, prompt: str) -> str:
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                if self.provider == "openai":
                    out = self._call_openai(prompt)
                elif self.provider == "anthropic":
                    out = self._call_anthropic(prompt)
                else:
                    raise ValueError(f"Unsupported LLM provider: {self.provider}")

                return out["text"]

            except Exception as e:
                last_error = e
                logging.error(
                    f"[LLM ERROR] Provider={self.provider} Model={self.model} "
                    f"Attempt {attempt}/{self.max_retries} — {e}"
                )
                time.sleep(2 ** attempt)

        raise RuntimeError(
            f"LLM failed after {self.max_retries} retries"
        ) from last_error

    # ============================================================
    # PUBLIC: JSON CALL
    # ============================================================
    def call_json(self, prompt: str) -> Dict[str, Any]:
        """
        Call LLM, parse response as JSON, retry on decode error.
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                text = self.call_text(prompt)
                return json.loads(text)

            except json.JSONDecodeError as e:
                last_error = e
                logging.warning(
                    f"[JSON ERROR] attempt {attempt}/{self.max_retries} — {e}"
                )
                time.sleep(1.2)

        raise RuntimeError(
            "LLM returned invalid JSON after multiple retries."
        ) from last_error