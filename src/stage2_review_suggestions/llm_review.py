from __future__ import annotations
from typing import Dict, Any, Optional

from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from .logger import logger

from src.utils.llm_client_realtime import LLMClientRealtime

_client = LLMClientRealtime()


def review_text_unit(
    *,
    unit_type: str,
    slide_id: str,
    content: str,
) -> Dict[str, Optional[str]]:

    user_prompt = USER_PROMPT_TEMPLATE.format(
        unit_type=unit_type,
        slide_id=slide_id,
        content=content,
    )

    response = _client.call_json_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        required_keys={"suggested", "notes"},
    )

    return {
        "suggested": response.get("suggested"),
        "notes": response.get("notes"),
    }

