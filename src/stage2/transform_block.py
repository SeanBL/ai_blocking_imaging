import json
from .prompt_blueprint import SYSTEM_PROMPT, build_user_prompt

def transform_block(block, llm):
    user_prompt = build_user_prompt(block)
    raw_output = llm.run(SYSTEM_PROMPT, user_prompt)

    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError:
        raise ValueError("LLM returned invalid JSON")

    return data