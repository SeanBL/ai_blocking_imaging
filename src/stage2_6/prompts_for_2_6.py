def sentence_shaping_prompt(panel_text: str) -> str:
    return f"""
THIS TASK IS SENTENCE SHAPING ONLY.

You are working on a SINGLE medical panel that is already finalized.

ABSOLUTE RULES (NO EXCEPTIONS):
- DO NOT add, remove, paraphrase, summarize, or rewrite ANY words.
- DO NOT change sentence wording.
- DO NOT change sentence order.
- DO NOT move content between panels.
- DO NOT invent content.
- DO NOT create new slides or panels.

TASK:
Group the existing sentences into sentence display blocks.

IMPORTANT:
- You MUST always return at least ONE group.
- If no splitting is required, return a SINGLE group containing the full panel text.

GROUPING RULES:
- If the panel contains EXACTLY 2 sentences:
  → Output TWO separate blocks, one sentence per block.
- If the panel contains EXACTLY 3 sentences:
  → Output TWO blocks that group the sentences in a pedagogically coherent way.
- If the panel contains MORE than 3 sentences:
  → Each block may contain a MAXIMUM of 2 sentences.

CRITICAL OUTPUT RULE:
- You MUST wrap your output in a top-level key called "sentence_shaping".
- If this key is missing, the output will be rejected.

RETURN JSON ONLY in this EXACT format:

{{
  "sentence_shaping": {{
    "sentence_blocks": [
      {{
        "header": "same header as input panel",
        "content": "Exact sentence text here."
      }}
    ]
  }}
}}

SOURCE PANEL TEXT (DO NOT MODIFY):
{panel_text}
""".strip()


