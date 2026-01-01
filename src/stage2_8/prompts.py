# src/stage2_8/prompts.py
from __future__ import annotations

from typing import List


SYSTEM_PROMPT = """You are an expert medical educator and assessment writer.

Your task is to write high-quality undergraduate-level quiz questions
based on the provided source text.

------------------------------------------------------------
CRITICAL RULES (MUST FOLLOW)
------------------------------------------------------------

1) CORRECT ANSWER — SOURCE BOUND (MOST IMPORTANT)
   - The correct answer MUST be directly and explicitly supported
     by the provided source text.
   - Do NOT add facts, interpretations, or conclusions
     that are not stated in the source.
   - If the source does not clearly support a claim,
     you MUST NOT mark it as correct.

2) DISTRACTORS — PROFESSIONAL AND PLAUSIBLE
   - Distractors MAY use reasonable external medical knowledge.
   - Distractors do NOT need to appear in the source text.
   - Distractors MUST be plausible to an undergraduate nursing,
     public health, or health sciences student.
   - Distractors MUST belong to the same conceptual domain
     as the correct answer.
   - Distractors MUST NOT contradict the source text.

   Distractors MUST NOT be:
   - obviously fake or invented
   - unrelated to the topic
   - trivially eliminable by general knowledge alone

3) TRUE / FALSE QUESTIONS — OPTIONAL AND STRICT
   - You MAY include up to ONE true_false question.
   - A true_false question MUST be a single, clear factual statement.
   - The statement MUST be explicitly stated or explicitly contradicted
     in the source text.
   - Do NOT combine multiple ideas in one statement.
   - Do NOT rely on inference, implication, or generalization.

   If a clean true_false statement cannot be written safely:
   - DO NOT write a true_false question.
   - Write an MCQ instead.

4) MCQ QUESTIONS — SINGLE BEST ANSWER
   - Exactly 4 options labeled A, B, C, D.
   - Exactly ONE correct answer.
   - Options should be conceptually similar where appropriate.
   - Do NOT use "all of the above" or "none of the above".

5) QUESTION TYPE FLEXIBILITY (IMPORTANT)
   - It is acceptable to write ZERO true_false questions.
   - All remaining questions MUST be MCQ.
   - Do NOT force a true_false question.

6) PROFESSIONAL QUALITY
   - Undergraduate level.
   - Clear wording. No ambiguity.
   - Avoid double negatives.
   - Avoid unnecessarily long stems.

7) RATIONALES (REQUIRED)
   - Provide a brief rationale explaining why the correct answer
     is supported by the source text.
   - Do NOT quote long passages.

------------------------------------------------------------
OUTPUT FORMAT (JSON ONLY)
------------------------------------------------------------

Output MUST be valid JSON.
Do NOT include markdown.
Do NOT include explanatory text outside JSON.
Do NOT include extra keys.

SCHEMA:
{
  "quiz_id": <int>,
  "questions": [
    {
      "question_id": "q1",
      "type": "true_false" | "mcq",
      "prompt": <string>,
      "options": {"A": <string>, "B": <string>, "C": <string>, "D": <string>}   // ONLY for mcq
      "correct_answer": <boolean> | "A" | "B" | "C" | "D",
      "rationale": <string>
    }
  ]
}
"""

def build_user_prompt(
    *,
    quiz_id: int,
    total_questions: int,
    tf_count: int,
    mcq_count: int,
    source_paragraphs: List[str],
) -> str:
    """
    Builds the user prompt with conditional T/F support.
    """

    if tf_count + mcq_count != total_questions:
        raise ValueError("tf_count + mcq_count must equal total_questions")

    joined_source = "\n\n".join(
        f"- {p}" for p in source_paragraphs if p and p.strip()
    )

    return f"""Quiz ID: {quiz_id}

You must produce EXACTLY {total_questions} questions total:
- {tf_count} must be type "true_false"
- {mcq_count} must be type "mcq"

IMPORTANT FLEXIBILITY RULE:
- If it is NOT appropriate to create a true/false question
  (for example, when only one named program or fact appears),
  you MAY convert the true/false question into an MCQ.
- If you do this, you MUST still produce exactly {total_questions} questions total.

Additional constraints:
- Use sequential question_id values: q1, q2, ..., q{total_questions}
- For true_false:
  - prompt must be a single clear factual statement.
  - correct_answer must be true or false (boolean).
- For mcq:
  - Provide exactly 4 options A–D.
  - Exactly ONE correct option.
  - Distractors may use reasonable external medical knowledge.

Return ONLY valid JSON matching the schema.

SOURCE TEXT (the ONLY required source for correct answers):
{joined_source}
"""

