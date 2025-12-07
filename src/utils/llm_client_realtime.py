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
    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        max_retries: int | None = None,
    ):
        # ------- Load API keys -------
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        if not self.openai_api_key and not self.anthropic_api_key:
            raise RuntimeError(
                "No API keys found. Ensure .env is loaded and OPENAI_API_KEY / ANTHROPIC_API_KEY exist."
            )

        # ------- Load YAML settings -------
        settings = load_settings()
        llm_settings = settings.get("llm", {})

        self.provider = provider or llm_settings.get("provider", "openai")
        self.model = model or llm_settings.get("model", "gpt-4o-mini")
        self.temperature = (
            temperature if temperature is not None else llm_settings.get("temperature", 0.0)
        )
        self.max_tokens = (
            max_tokens if max_tokens is not None else llm_settings.get("max_output_tokens", 2048)
        )
        self.max_retries = (
            max_retries if max_retries is not None else llm_settings.get("retry_limit", 5)
        )

        # ------- Create OpenAI client immediately -------
        self._openai_client = OpenAI(api_key=self.openai_api_key)

        # ------- Anthropic client lazy-loaded later -------
        self._anthropic_client: Anthropic | None = None

    # ============================================================
    # OPENAI CALL
    # ============================================================

    def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """
        Calls the OpenAI Chat Completions endpoint using the modern client.
        """
        response = self._openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        usage = response.usage or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))

        # Log cost usage
        log_usage(self.model, prompt_tokens, completion_tokens, provider="openai")

        return {
            "text": response.choices[0].message.content,
            "usage": usage,
        }

    # ============================================================
    # ANTHROPIC CALL
    # ============================================================

    def _call_anthropic(self, prompt: str) -> Dict[str, Any]:
        """
        Calls the Anthropic Messages API.
        """

        # Initialize only when first used
        if self._anthropic_client is None:
            self._anthropic_client = Anthropic(api_key=self.anthropic_api_key)

        msg = self._anthropic_client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        text = msg.content[0].text if msg.content else ""
        usage = getattr(msg, "usage", {}) or {}

        prompt_tokens = int(usage.get("input_tokens", 0))
        completion_tokens = int(usage.get("output_tokens", 0))

        # Log cost usage
        log_usage(self.model, prompt_tokens, completion_tokens, provider="anthropic")

        return {
            "text": text,
            "usage": usage,
        }

    # ============================================================
    # PUBLIC: RAW TEXT CALL
    # ============================================================

    def call_text(self, prompt: str) -> str:
        """
        Call the LLM and return raw text, with retries.
        """
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                if self.provider == "openai":
                    out = self._call_openai(prompt)
                    return out["text"]

                elif self.provider == "anthropic":
                    out = self._call_anthropic(prompt)
                    return out["text"]

                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")

            except Exception as e:
                last_error = e
                logging.error(
                    f"LLM error (provider={self.provider}, model={self.model}) attempt "
                    f"{attempt}/{self.max_retries}: {e}"
                )
                time.sleep(2 ** attempt)  # exponential backoff

        raise RuntimeError(f"LLM failed after {self.max_retries} attempts") from last_error

    # ============================================================
    # PUBLIC: JSON CALL
    # ============================================================

    def call_json(self, prompt: str) -> Dict[str, Any]:
        """
        Call the LLM and parse the response as JSON, retrying on decode errors.
        """
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                text = self.call_text(prompt)
                return json.loads(text)

            except json.JSONDecodeError as e:
                last_error = e
                logging.warning(
                    f"JSON decode error (attempt {attempt}/{self.max_retries}). "
                    "Retrying..."
                )
                time.sleep(1.5)

        raise RuntimeError("Failed to parse valid JSON from LLM") from last_error