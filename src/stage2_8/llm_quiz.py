# src/stage2_8/llm_quiz.py
from __future__ import annotations

from typing import Any, Dict, List

from .logger import logger
from .llm_call import call_llm_json

from .llm_concepts import generate_source_claims
from .llm_blueprints import generate_question_blueprints

from .prompts_author_single import (
    AUTHOR_SINGLE_SYSTEM_PROMPT,
    build_author_single_user_prompt,
)
from .validate_quiz_post_assembly import validate_quiz_post_assembly

def validate_single_question(
    *,
    question: Dict[str, Any],
    question_id: str,
    quiz_id: int,
) -> None:
    """
    Validate ONE authored question before quiz assembly.
    Raises ValueError on any violation.
    """

    if not isinstance(question, dict):
        raise ValueError("Question must be an object")

    required_keys = {
        "question_id",
        "type",
        "prompt",
        "correct_answer",
        "rationale",
        "quiz_role",
        "question_style",
        "cognitive_level",
        "claim_ids",
    }

    missing = required_keys - set(question.keys())
    if missing:
        raise ValueError(
            f"[V2] Missing keys {missing} — quiz_id={quiz_id}, question={question_id}"
        )

    role = question.get("quiz_role")
    if role not in ("inline_direct", "final_direct", "module_application"):
        raise ValueError(
            f"[V2] Invalid quiz_role '{role}' — quiz_id={quiz_id}, question={question_id}"
        )

    qtype = question.get("type")
    if qtype not in ("mcq", "true_false"):
        raise ValueError(
            f"[V2] Invalid type '{qtype}' — quiz_id={quiz_id}, question={question_id}"
        )

    # -----------------------
    # Prompt + rationale
    # -----------------------
    if not isinstance(question["prompt"], str) or not question["prompt"].strip():
        raise ValueError(
            f"[V2] Empty prompt — quiz_id={quiz_id}, question={question_id}"
        )

    if not isinstance(question["rationale"], str) or not question["rationale"].strip():
        raise ValueError(
            f"[V2] Empty rationale — quiz_id={quiz_id}, question={question_id}"
        )

    # -----------------------
    # TRUE / FALSE
    # -----------------------
    if qtype == "true_false":
        if "options" in question:
            raise ValueError(
                f"[V2] true_false must not include options — quiz_id={quiz_id}, question={question_id}"
            )

        if not isinstance(question["correct_answer"], bool):
            raise ValueError(
                f"[V2] true_false correct_answer must be boolean — quiz_id={quiz_id}, question={question_id}"
            )

    # -----------------------
    # MCQ
    # -----------------------
    if qtype == "mcq":
        options = question.get("options")

        if not isinstance(options, dict):
            raise ValueError(
                f"[V2] mcq options must be object — quiz_id={quiz_id}, question={question_id}"
            )

        if set(options.keys()) != {"A", "B", "C", "D"}:
            raise ValueError(
                f"[V2] mcq options must be A–D — quiz_id={quiz_id}, question={question_id}"
            )

        for k, v in options.items():
            if not isinstance(v, str) or not v.strip():
                raise ValueError(
                    f"[V2] mcq option {k} empty — quiz_id={quiz_id}, question={question_id}"
                )

        if question["correct_answer"] not in ("A", "B", "C", "D"):
            raise ValueError(
                f"[V2] mcq correct_answer invalid — quiz_id={quiz_id}, question={question_id}"
            )



# --------------------------------------------------
# HARD INVARIANT: SINGLE-QUESTION AUTHORING ONLY
# --------------------------------------------------

def generate_quiz_questions(
    *,
    quiz_id: int,
    source_paragraphs: List[str],
    inline_direct_questions: int,
    final_direct_questions: int,
    module_application_questions: int = 1,
) -> Dict[str, Any]:
    """
    Gold-standard 3-pass quiz generation (V2, SAFE):

      Pass 1: Source claims (source-locked)
      Pass 2: Question blueprints (role-aware)
      Pass 3: Author writes ONE question per request
              (Python assembles final quiz JSON)
    """

    total_questions = (
        inline_direct_questions
        + final_direct_questions
        + module_application_questions
    )

    logger.info(
        f"[V2] 3-pass quiz generation starting — quiz_id={quiz_id}, "
        f"inline_direct={inline_direct_questions}, "
        f"final_direct={final_direct_questions}, "
        f"module_application={module_application_questions}, "
        f"total_questions={total_questions}"
    )

    # ----------------------------
    # PASS 1 — SOURCE CLAIMS
    # ----------------------------
    claims_payload = generate_source_claims(
        quiz_id=quiz_id,
        source_paragraphs=source_paragraphs,
        concept_count=max(6, total_questions + 2),
    )

    source_claims = claims_payload.get("source_claims", [])
    if not source_claims:
        raise ValueError(f"[V2] No source claims generated — quiz_id={quiz_id}")

    logger.info(
        f"[V2] Pass 1 complete — quiz_id={quiz_id}, claims={len(source_claims)}"
    )

    # ----------------------------
    # PASS 2 — BLUEPRINTS
    # ----------------------------
    trimmed_claims = dict(claims_payload)
    trimmed_claims["source_claims"] = trimmed_claims["source_claims"][: total_questions + 2]

    blueprints_payload = generate_question_blueprints(
        quiz_id=quiz_id,
        source_claims_payload=trimmed_claims,
        inline_direct_questions=inline_direct_questions,
        final_direct_questions=final_direct_questions,
        module_application_questions=module_application_questions,
    )

    blueprints = blueprints_payload.get("blueprints", [])
    if len(blueprints) != total_questions:
        raise ValueError(
            f"[V2] Blueprint count mismatch — quiz_id={quiz_id}, "
            f"expected={total_questions}, actual={len(blueprints)}"
        )

    logger.info(
        f"[V2] Pass 2 complete — quiz_id={quiz_id}, blueprints={len(blueprints)}"
    )

    # ----------------------------
    # PASS 3 — AUTHOR (SINGLE QUESTION)
    # ----------------------------
    questions: List[Dict[str, Any]] = []

    for idx, blueprint in enumerate(blueprints, start=1):
        question_id = f"q{idx}"

        user_prompt = build_author_single_user_prompt(
            quiz_id=quiz_id,
            question_id=question_id,
            source_paragraphs=source_paragraphs,
            source_claims=source_claims,
            blueprint=blueprint,
        )

        prompt = AUTHOR_SINGLE_SYSTEM_PROMPT + "\n\n" + user_prompt

        logger.info(
            f"[V2] Author single-question invoked — quiz_id={quiz_id}, question={question_id}"
        )

        MAX_ATTEMPTS = 2
        last_error: Exception | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                parsed_question = call_llm_json(
                    prompt=prompt,
                    stage_tag=f"Stage 2.8 Author Single (attempt {attempt})",
                )

                parsed_question["question_id"] = question_id
                # ✅ Preserve blueprint metadata for downstream routing/assembly
                parsed_question["quiz_role"] = blueprint.get("quiz_role")
                parsed_question["question_style"] = blueprint.get("question_style")
                parsed_question["cognitive_level"] = blueprint.get("cognitive_level")
                parsed_question["claim_ids"] = blueprint.get("claim_ids")

                validate_single_question(
                    question=parsed_question,
                    question_id=question_id,
                    quiz_id=quiz_id,
                )

                questions.append(parsed_question)

                logger.info(
                    f"[V2] Author completed — quiz_id={quiz_id}, question={question_id}, attempt={attempt}"
                )
                break

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[V2] Author failed — quiz_id={quiz_id}, question={question_id}, attempt={attempt}"
                )

        else:
            raise RuntimeError(
                f"[V2] Author failed after {MAX_ATTEMPTS} attempts — "
                f"quiz_id={quiz_id}, question={question_id}"
            ) from last_error

    # ----------------------------
    # ORDERING + ASSEMBLY
    # ----------------------------
    questions_sorted = sorted(
        questions,
        key=lambda q: int(q["question_id"].replace("q", ""))
    )

    expected_ids = [f"q{i}" for i in range(1, total_questions + 1)]
    actual_ids = [q["question_id"] for q in questions_sorted]

    if actual_ids != expected_ids:
        raise ValueError(
            f"[V2] Question ordering mismatch — quiz_id={quiz_id}, "
            f"expected={expected_ids}, actual={actual_ids}"
        )

    final_quiz = {
        "quiz_id": quiz_id,
        "questions": questions_sorted,
    }

    logger.info(
        f"[V2] Quiz assembly complete — quiz_id={quiz_id}, questions={len(questions)}"
    )

    validate_quiz_post_assembly(quiz_payload=final_quiz)

    return final_quiz
