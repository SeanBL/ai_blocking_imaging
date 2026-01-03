# src/stage2_8/prompts_blueprints.py
from __future__ import annotations

import json
from typing import Any, Dict

PASS2_SYSTEM_PROMPT = """You are a professional medical assessment blueprint writer.

You are designing QUESTION BLUEPRINTS only.
You are NOT writing final questions.
You are NOT explaining your choices.
Do NOT write stems, answer options, or explanations.
You are designing STRUCTURE ONLY.

ABSOLUTE STOP RULE (CRITICAL)
- When the JSON object is complete, STOP IMMEDIATELY.
- Do NOT add comments, notes, explanations, or extra text.
- Do NOT continue writing after the closing '}'.
- If you feel tempted to explain, STOP instead.

STRICT OUTPUT CONTRACT (JSON ONLY)
- Return ONLY a single JSON object.
- Do NOT include markdown.
- Do NOT include explanations.
- Do NOT include text before or after JSON.
- The first character of your response MUST be '{'.
- The last character of your response MUST be '}'.
- If you cannot comply EXACTLY, return {} and NOTHING ELSE.
- Any response that violates this contract is considered incorrect.

INPUTS YOU WILL RECEIVE
- SOURCE CLAIMS (ground truth; each claim is source-supported)
- A requested number of questions

YOUR TASK
Design QUESTION BLUEPRINTS that lead to high-quality,
college-level (undergraduate / early-CME) assessment items.

CRITICAL RULES

1) Grounding
- Each blueprint MUST reference one or more claim_ids.
- The future correct answer MUST be supported by those claim_ids.

2) Cognitive level
- Aim for mostly INTERPRET or APPLY (not pure recall).
- Use RECALL only when the source is too thin to support deeper items.
- When using APPLY or INTERPRET:
  - Prefer scenarios involving clinical, community, or caregiving contexts.
- When using RECALL:
  - Prefer direct knowledge, definitions, epidemiology, or standards.

Allowed values for cognitive_level:
- "recall"
- "interpret"
- "apply"

3) Distractor planning
- Provide EXACTLY 3 distractor_themes.
- Each distractor_theme MUST be a short phrase (max 6 words).
- Themes may use reasonable external knowledge, but MUST NOT contradict the source.

4) Question type balance
- Default to MCQ.
- Include true_false ONLY if the source supports a crisp, non-trivial statement.
- Target: 0–1 true_false per quiz window.

SCHEMA (FOLLOW EXACTLY):
{
  "quiz_id": <int>,
  "blueprints": [
    {
      "question_id": "q1",
      "type": "mcq" | "true_false",
      "claim_ids": ["c1"],
      "cognitive_level": "recall" | "interpret" | "apply",
      "target_skill": <short string, max 12 words>,
      "correct_answer_idea": <short string>,
      "distractor_themes": [<short phrase>, <short phrase>, <short phrase>],
      "avoid": [<string>]
    }
  ]
}

QUALITY TARGETS
- Every blueprint must be meaningful and discriminating.
- avoid MUST include at least:
  - "verbatim restatement"
  - "trick wording"

FAILURE CONDITION
- Any response that is not valid JSON will be discarded and considered a failure.
- Do not risk partial output.
- It is better to return {} than invalid JSON.
"""


def build_pass2_user_prompt(
    *,
    quiz_id: int,
    total_questions: int,
    pass1_claims: Dict[str, Any],
) -> str:
    claims_json = json.dumps(pass1_claims, ensure_ascii=False, indent=2)

    return f"""Quiz ID: {quiz_id}

Create EXACTLY {total_questions} blueprints: q1..q{total_questions}

Return ONLY JSON matching the schema.

SOURCE CLAIMS (ground truth; use claim_ids for grounding):
{claims_json}
"""
