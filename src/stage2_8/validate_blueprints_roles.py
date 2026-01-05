# src/stage2_8/validate_blueprints_roles.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class BlueprintValidationResult:
    ok: bool
    errors: List[str]
    role_counts: Dict[str, int]


REQUIRED_KEYS = {
    "question_id",
    "type",
    "quiz_role",
    "question_style",
    "claim_ids",
    "cognitive_level",
    "target_skill",
    "correct_answer_idea",
    "distractor_themes",
    "avoid",
}

ALLOWED_TYPES = {"mcq", "true_false"}
ALLOWED_ROLES = {"inline_direct", "final_direct", "module_application"}
ALLOWED_STYLES = {"direct", "scenario"}
ALLOWED_COG = {"recall", "interpret", "apply"}


def _count_roles(blueprints: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {r: 0 for r in ALLOWED_ROLES}
    for bp in blueprints:
        role = bp.get("quiz_role")
        if role in counts:
            counts[role] += 1
    return counts


def validate_pass2_blueprints(
    *,
    payload: Dict[str, Any],
    expected_inline_direct: int,
    expected_final_direct: int,
    expected_module_application: int = 1,
    expected_total: int | None = None,
) -> BlueprintValidationResult:
    """
    Strict validator for Pass-2 blueprint output.

    Assertions enforced:
      - payload contains quiz_id and blueprints list
      - exact blueprint counts by quiz_role
      - role constraints:
          inline_direct/final_direct -> direct + recall/interpret
          module_application -> scenario + apply
      - question_id uniqueness and expected sequence q1..qN (if expected_total provided)
    """
    errors: List[str] = []

    if not isinstance(payload, dict):
        return BlueprintValidationResult(False, ["payload is not a dict"], {})

    quiz_id = payload.get("quiz_id")
    if not isinstance(quiz_id, int):
        errors.append("quiz_id must be an int")

    blueprints = payload.get("blueprints")
    if not isinstance(blueprints, list) or not blueprints:
        errors.append("blueprints must be a non-empty list")
        return BlueprintValidationResult(False, errors, {})

    # Expected total (optional but recommended)
    if expected_total is not None and len(blueprints) != expected_total:
        errors.append(
            f"expected_total mismatch: expected {expected_total}, got {len(blueprints)}"
        )

    # Validate each blueprint
    seen_qids = set()
    for i, bp in enumerate(blueprints, start=1):
        if not isinstance(bp, dict):
            errors.append(f"blueprints[{i}] is not a dict")
            continue

        missing = REQUIRED_KEYS - set(bp.keys())
        if missing:
            errors.append(f"{bp.get('question_id', f'index_{i}')} missing keys: {sorted(missing)}")

        qid = bp.get("question_id")
        if not isinstance(qid, str) or not qid.startswith("q"):
            errors.append(f"blueprints[{i}] invalid question_id: {qid!r}")
        else:
            if qid in seen_qids:
                errors.append(f"duplicate question_id: {qid}")
            seen_qids.add(qid)

        qtype = bp.get("type")
        if qtype not in ALLOWED_TYPES:
            errors.append(f"{qid} invalid type: {qtype!r}")

        role = bp.get("quiz_role")
        if role not in ALLOWED_ROLES:
            errors.append(f"{qid} invalid quiz_role: {role!r}")

        style = bp.get("question_style")
        if style not in ALLOWED_STYLES:
            errors.append(f"{qid} invalid question_style: {style!r}")

        cog = bp.get("cognitive_level")
        if cog not in ALLOWED_COG:
            errors.append(f"{qid} invalid cognitive_level: {cog!r}")

        claim_ids = bp.get("claim_ids")
        if not isinstance(claim_ids, list) or not claim_ids or not all(isinstance(x, str) for x in claim_ids):
            errors.append(f"{qid} claim_ids must be a non-empty list[str]")

        distractors = bp.get("distractor_themes")
        if (
            not isinstance(distractors, list)
            or len(distractors) != 3
            or not all(isinstance(x, str) and x.strip() for x in distractors)
        ):
            errors.append(f"{qid} distractor_themes must be exactly 3 non-empty strings")

        avoid = bp.get("avoid")
        if not isinstance(avoid, list) or not all(isinstance(x, str) for x in avoid):
            errors.append(f"{qid} avoid must be list[str]")
        else:
            # Required avoid items
            required_avoid = {"verbatim restatement", "trick wording"}
            if not required_avoid.issubset({a.strip().lower() for a in avoid}):
                errors.append(
                    f"{qid} avoid must include: {sorted(required_avoid)}"
                )

        # Role constraints (core)
        if role in {"inline_direct", "final_direct"}:
            if style != "direct":
                errors.append(f"{qid} role {role} must have question_style='direct'")
            if cog not in {"recall", "interpret"}:
                errors.append(f"{qid} role {role} must have cognitive_level='recall' or 'interpret'")

        if role == "module_application":
            if style != "scenario":
                errors.append(f"{qid} role module_application must have question_style='scenario'")
            if cog != "apply":
                errors.append(f"{qid} role module_application must have cognitive_level='apply'")

    # Enforce role counts exactly
    role_counts = _count_roles(blueprints)

    if role_counts.get("inline_direct", 0) != expected_inline_direct:
        errors.append(
            f"role count mismatch inline_direct: expected {expected_inline_direct}, got {role_counts.get('inline_direct', 0)}"
        )
    if role_counts.get("final_direct", 0) != expected_final_direct:
        errors.append(
            f"role count mismatch final_direct: expected {expected_final_direct}, got {role_counts.get('final_direct', 0)}"
        )
    if role_counts.get("module_application", 0) != expected_module_application:
        errors.append(
            f"role count mismatch module_application: expected {expected_module_application}, got {role_counts.get('module_application', 0)}"
        )

    # Enforce question_id sequence q1..qN if expected_total known
    if expected_total is not None:
        expected_ids = {f"q{i}" for i in range(1, expected_total + 1)}
        if seen_qids != expected_ids:
            missing_ids = sorted(expected_ids - seen_qids)
            extra_ids = sorted(seen_qids - expected_ids)
            if missing_ids:
                errors.append(f"missing question_ids: {missing_ids}")
            if extra_ids:
                errors.append(f"unexpected question_ids: {extra_ids}")

    return BlueprintValidationResult(ok=(len(errors) == 0), errors=errors, role_counts=role_counts)
