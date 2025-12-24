# src/stage2_5/prompts.py

def panel_semantic_slides_prompt(header: str, source_text: str) -> str:
    return f"""
THIS TASK IS PANEL SPLITTING ONLY.

You are splitting a medical PANEL into multiple PANELS.

ABSOLUTE RULES (NO EXCEPTIONS):
- DO NOT add, remove, paraphrase, summarize, or rewrite ANY words.
- ALL wording must remain EXACTLY as written.
- DO NOT change sentence wording or order.
- DO NOT invent content.
- DO NOT create engage slides.
- DO NOT split bullet lists.

GOAL:
Split the panel into 2 or more panels if the total length exceeds 70 words.

CONSTRAINTS:
- Each resulting panel MUST be 30–70 words.
- If a panel would be under 30 words, MERGE it with the nearest adjacent panel.
- Preserve pedagogical coherence.

OUTPUT FORMAT (JSON ONLY):
{{
  "slides": [
    {{
      "header": "{header}",
      "content": "<exact text slice>"
    }},
    {{
      "header": "{header} (continued)",
      "content": "<exact text slice>"
    }}
  ]
}}

SOURCE TEXT (DO NOT MODIFY):
{source_text}
""".strip()




def strict_sentence_reflow_prompt(text: str) -> str:
    return f"""
You are performing STRICT sentence boundary detection.

ABSOLUTE RULES:
- You MUST NOT rewrite, paraphrase, summarize, or edit any text.
- You MUST NOT output any words from the text.
- You MUST NOT add or remove content.
- You MAY ONLY return character indexes.

TASK:
Identify sentence boundaries in the text below.
Return a list of starting character indexes for each sentence.

The first index MUST be 0.
Indexes MUST be sorted.
Indexes MUST reconstruct the text EXACTLY when sliced.

RETURN ONLY VALID JSON in this exact format:

{{
  "sentence_reflow": {{
    "action": "reflow",
    "indexes": [0, 123, 456]
  }},
  "safety": {{
    "adds_new_information": false,
    "removes_information": false,
    "medical_facts_changed": false,
    "policy_violation": false
  }}
}}

TEXT (DO NOT COPY WORDS FROM HERE):
{text}
""".strip()



def engage1_item_review_prompt(items: list[str]) -> str:
    joined = "\n".join(f"{i}. {t}" for i, t in enumerate(items))
    return f"""
You are assisting in a medical education pipeline.

STRICT RULES:
- Slide is already ENGAGE 1.
- Do NOT add or remove items.
- Do NOT change interaction type.

Task:
Review each engage item for length.
Preferred ≤ 50 words (70 max).
Suggest tightening ONLY if limits are exceeded.

Return JSON ONLY.

ENGAGE ITEMS:
{joined}
""".strip()


def button_label_prompt(context: str) -> str:
    return f"""
You are assisting in a medical education pipeline.

STRICT RULES:
- Do NOT invent new concepts.
- Button labels must be ≤ 4 words.
- No punctuation.

Task:
Suggest concise button labels if current labels are invalid.

Return JSON ONLY.

CONTEXT:
{context}
""".strip()

def semantic_index_prompt(sentences: list[str]) -> str:
    joined = "\n".join(
        f"{i}. {s}" for i, s in enumerate(sentences)
    )

    return f"""
You are grouping sentences into coherent instructional panels.

STRICT RULES:
- DO NOT rewrite or paraphrase any sentence
- DO NOT remove or add information
- DO NOT change order
- ONLY group sentence indices

Return ONLY valid JSON.

Sentences:
{joined}

JSON FORMAT:
{{
  "semantic_index": {{
    "groups": [[0,1],[2]],
    "reason": "Why these sentences belong together"
  }},
  "safety": {{
    "adds_new_information": false,
    "removes_information": false,
    "medical_facts_changed": false
  }}
}}
""".strip()