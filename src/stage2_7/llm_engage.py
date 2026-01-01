import json


SYSTEM_PROMPT = (
    "You are a medical editor and instructional designer.\n"
    "Your task is to restructure medical content into interactive engages.\n\n"
    "STRICT RULES (NON-NEGOTIABLE):\n"
    "- Preserve ALL medical meaning AND ALL original wording exactly.\n"
    "- Do NOT add, remove, invent, paraphrase, merge, split, or rewrite text.\n"
    "- Do NOT summarize, simplify, or reorganize sentence wording.\n"
    "- You may ONLY move existing sentences into a new structure.\n"
    "- ALL sentences from SOURCE_TEXT must appear EXACTLY ONCE in the output.\n"
    "- If text does not fit cleanly, include it anyway without modification.\n"
    "- Return ONLY valid JSON. No commentary. No explanations.\n"
)


ENGAGE1_PROMPT = """
Create an Engage 1 interaction from the SOURCE_TEXT.

Rules:
- Use the beginning of SOURCE_TEXT for the intro.
- ALL remaining sentences must be placed into items.
- Each item.text MUST be copied verbatim from SOURCE_TEXT.
- Do NOT rewrite, paraphrase, merge, split, or simplify sentences.
- Do NOT omit any sentence.
- You may only group existing sentences.
- Create 3–7 items IF POSSIBLE; if not possible, use as many items as needed
  to include ALL text without modification.
- Each item must include:
  - button_label (2–5 words, no punctuation; label may summarize but text may NOT)
  - text (verbatim copy from SOURCE_TEXT)
  - image: null

Return JSON EXACTLY in this format:
{{
  "type": "engage",
  "intro": {{ "text": "..." }},
  "items": [
    {{ "button_label": "...", "text": "...", "image": null }}
  ]
}}

SOURCE_TEXT:
<<<
{source_text}
>>>
"""


ENGAGE2_PROMPT = """
Create an Engage 2 interaction from the SOURCE_TEXT.

Rules:
- Use the beginning of SOURCE_TEXT for the intro.
- ALL remaining sentences must be placed into steps.
- Each step.text MUST be copied verbatim from SOURCE_TEXT.
- Do NOT rewrite, paraphrase, merge, split, or simplify sentences.
- Do NOT omit any sentence.
- You may ONLY move sentences into sequential steps.
- Create 3–8 steps IF POSSIBLE; if not possible, use as many steps as needed
  to include ALL text without modification.
- One button controls progression.
- button_label may summarize progression but MUST NOT alter text meaning.

Return JSON EXACTLY in this format:
{{
  "type": "engage2",
  "intro": {{ "text": "..." }},
  "steps": [
    {{ "text": "..." }}
  ],
  "button_label": "..."
}}

SOURCE_TEXT:
<<<
{source_text}
>>>
"""


def _strip_code_fences(text: str) -> str:
    """
    Remove ``` or ```json fences from LLM output if present.
    """
    text = text.strip()

    # Remove opening fence
    if text.startswith("```"):
        text = text.split("\n", 1)[1]

    # Remove closing fence
    if text.endswith("```"):
        text = text.rsplit("\n", 1)[0]

    return text.strip()


def synthesize_engage(source_text: str, engage_type: str, client) -> dict:
    """
    Call LLM to synthesize an Engage 1 or Engage 2 block.
    Text-frozen: no paraphrasing allowed.
    """
    if engage_type == "engage":
        prompt = ENGAGE1_PROMPT.format(source_text=source_text)
    elif engage_type == "engage2":
        prompt = ENGAGE2_PROMPT.format(source_text=source_text)
    else:
        raise ValueError(f"Unknown engage_type: {engage_type}")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    content = response.choices[0].message.content

    print("\n--- RAW LLM OUTPUT ---")
    print(content)
    print("--- END RAW LLM OUTPUT ---\n")

    clean = _strip_code_fences(content)
    return json.loads(clean)
