from __future__ import annotations
import json
import logging

from ..utils.llm_client_realtime import LLMClientRealtime
from ..utils.config_loader import load_prompt
from .prompt_blueprint import build_user_prompt


def transform_block(block, llm: LLMClientRealtime) -> dict:
    """
    Stage 2A – Text Transformation
    --------------------------------
    Takes a ParsedBlock from Stage 1 and returns the transformed
    instructional JSON structure.

    Uses:
      - SYSTEM prompt from config/prompt_blueprint.txt
      - USER prompt generated from prompt_blueprint.build_user_prompt()
      - Realtime LLM client with JSON parsing + retries
    """

    # 1) Load system prompt (full rewrite logic + rules)
    system_prompt = load_prompt("prompt_blueprint.txt")

    # 2) Build user prompt for this block
    user_prompt = build_user_prompt(block)

    # 3) Merge them
    full_prompt = system_prompt + "\n\n" + user_prompt

    logging.info(f"Calling LLM for block: {block.header}")

    # 4) Call the model and parse JSON
    response_json = llm.call_json(full_prompt)

    # 5) Validate minimal structure (optional but helpful)
    if "header" not in response_json:
        raise ValueError("Stage 2A response missing 'header' field")

    if "pages" not in response_json or not isinstance(response_json["pages"], list):
        raise ValueError("Stage 2A response missing 'pages' array")

    # 6) Return final structured JSON
    return response_json