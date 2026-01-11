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

def _extract_json_block(text: str) -> str | None:
    """
    Extract the outermost JSON object from text.
    Returns None if no valid JSON block is found.
    """
    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return None

    return text[start : end + 1]

# -------------------------------------------------
# Public helper: call LLM and return JSON
# -------------------------------------------------
def call_llm_json(
    *,
    prompt: str,
    model: str = "gpt-5.2-2025-12-11",
    temperature: float = 0.0,
    max_tokens: int = 4500,
    max_retries: int = 3,
    stage_tag: str = "Stage 2.8",
) -> Dict[str, Any]:

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.responses.create(
                model=model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",  # ✅ FIXED
                                "text": (
                                    prompt
                                    + "\n\nIMPORTANT:\n"
                                    "- Return ONLY a single valid JSON object.\n"
                                    "- No markdown.\n"
                                    "- No extra text.\n"
                                    "- First character must be '{'.\n"
                                    "- Last character must be '}'."
                                ),
                            }
                        ],
                    }
                ],
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            output = response.output_text

            if not output or not output.strip():
                raise ValueError("LLM returned empty response")

            try:
                return json.loads(output)

            except json.JSONDecodeError:
                # --- Attempt safe recovery: trim to outer JSON ---
                repaired = _extract_json_block(output)

                if repaired:
                    try:
                        return json.loads(repaired)
                    except json.JSONDecodeError:
                        pass  # fall through to debug + retry

                # 🔍 DEBUG: capture raw output once per failure
                debug_path = f"debug_pass1_{stage_tag.replace(' ', '_')}.txt"

                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write("===== RAW MODEL OUTPUT =====\n")
                    f.write(output)
                    f.write("\n\n===== END =====\n")

                logging.error(
                    f"[{stage_tag}] JSON parse failed even after repair. "
                    f"Raw output written to {debug_path}"
                )
                raise

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
