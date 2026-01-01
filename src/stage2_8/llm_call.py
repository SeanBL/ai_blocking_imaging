from __future__ import annotations

import json
import time
import logging
import os
from typing import Dict, Any

from dotenv import load_dotenv
from openai import OpenAI

# -------------------------------------------------
# Load environment variables (.env)
# -------------------------------------------------
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in .env")

client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------------------------------
# Public helper: call LLM and return JSON
# -------------------------------------------------
def call_llm_json(
    *,
    prompt: str,
    model: str = "gpt-5.2-2025-12-11",
    temperature: float = 0.0,
    max_tokens: int = 1200,
    max_retries: int = 3,
    stage_tag: str = "Stage 2.8",
) -> Dict[str, Any]:
    """
    Call OpenAI with a prompt and return parsed JSON.
    Retries on API or JSON errors.

    This function intentionally mirrors Stage 2.5 behavior.
    """

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_completion_tokens=max_tokens,
            )

            text = response.choices[0].message.content
            return json.loads(text)

        except json.JSONDecodeError as e:
            last_error = e
            logging.warning(
                f"[{stage_tag}] JSON decode failed "
                f"(attempt {attempt}/{max_retries})"
            )
            time.sleep(1.0)

        except Exception as e:
            last_error = e
            logging.error(
                f"[{stage_tag}] LLM call failed "
                f"(attempt {attempt}/{max_retries}): {e}"
            )
            time.sleep(2 ** attempt)

    raise RuntimeError(
        f"{stage_tag} LLM failed after retries"
    ) from last_error
