from __future__ import annotations

import time
import json
import logging
from typing import Any, Dict, Set, Optional

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
    Unified interface for OpenAI + Anthropic with:
    - retry logic
    - JSON enforcement
    - system + user prompt support
    - pipeline-safe validation
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
        self.model = model or llm_settings.get("model", "gpt-5.2-2025-12-11")

        self.temperature = (
            temperature if temperature is not None
            else llm_settings.get("temperature", 0.0)
        )

        self.max_tokens = (
            max_tokens if max_tokens is not None
            else llm_settings.get("max_output_tokens", 2048)
        )

        self.max_retries = (
            max_retries if max_retries is not None
            else llm_settings.get("retry_limit", 5)
        )

        self._openai_client = OpenAI(api_key=self.openai_api_key)
        self._anthropic_client: Anthropic | None = None

    # ============================================================
    # PROVIDER CALLS
    # ============================================================
    def _call_openai(self, messages: list[dict[str, str]]) -> str:
        response = self._openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_completion_tokens=self.max_tokens,
        )

        usage = response.usage
        log_usage(
            model=self.model,
            prompt_tokens=getattr(usage, "prompt_tokens", 0),
            completion_tokens=getattr(usage, "completion_tokens", 0),
            provider="openai",
        )

        return response.choices[0].message.content

    def _call_anthropic(self, messages: list[dict[str, str]]) -> str:
        if self._anthropic_client is None:
            self._anthropic_client = Anthropic(api_key=self.anthropic_api_key)

        msg = self._anthropic_client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=messages,
        )

        usage = getattr(msg, "usage", None)
        log_usage(
            model=self.model,
            prompt_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            provider="anthropic",
        )

        return msg.content[0].text if msg.content else ""

    # ============================================================
    # CORE CALL WITH RETRY
    # ============================================================
    def _call_with_retry(self, messages: list[dict[str, str]]) -> str:
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                if self.provider == "openai":
                    return self._call_openai(messages)
                elif self.provider == "anthropic":
                    return self._call_anthropic(messages)
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")

            except Exception as e:
                last_error = e
                logging.error(
                    f"[LLM ERROR] Provider={self.provider} Model={self.model} "
                    f"Attempt {attempt}/{self.max_retries} — {e}"
                )
                time.sleep(2 ** attempt)

        raise RuntimeError("LLM failed after retries") from last_error

    # ============================================================
    # PUBLIC: STRUCTURED JSON CALL (PIPELINE SAFE)
    # ============================================================
    def call_json_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        required_keys: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """
        Canonical pipeline-safe JSON call.
        """

        messages = [
            {"role": "system", "content": system_prompt.strip()},
            {
                "role": "user",
                "content": (
                    user_prompt.strip()
                    + "\n\nReturn ONLY valid JSON."
                ),
            },
        ]

        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                text = self._call_with_retry(messages)
                data = json.loads(text)

                if required_keys:
                    missing = required_keys - data.keys()
                    if missing:
                        raise ValueError(
                            f"Missing required keys in LLM response: {missing}"
                        )

                return data

            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                logging.warning(
                    f"[JSON ERROR] attempt {attempt}/{self.max_retries} — {e}"
                )
                time.sleep(1.5)

        raise RuntimeError(
            "LLM returned invalid structured JSON after retries"
        ) from last_error

    def call_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        required_keys: set[str] | None = None,
    ) -> Dict[str, Any]:
        """
        Compatibility wrapper for legacy code.
        Delegates to call_json_structured().
        """
        return self.call_json_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            required_keys=required_keys,
        )