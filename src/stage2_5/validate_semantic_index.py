from __future__ import annotations

from typing import Any, Dict, List, Tuple, Set


def _fail(reason: str) -> Tuple[bool, Dict[str, Any]]:
    return False, {
        "rejected": True,
        "reason": reason,
    }


def _ok(obj: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    return True, obj


def validate_semantic_index(
    obj: Any,
    sentence_count: int,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate SEMANTIC_INDEX output.

    Rules enforced:
    - semantic_index.groups must be a list of lists of integers
    - indices must be valid sentence indices
    - indices must appear exactly once
    - order must be preserved
    - safety block must exist and be false for all flags
    """

    if not isinstance(obj, dict):
        return _fail("semantic_index output must be an object")

    semantic = obj.get("semantic_index")
    if not isinstance(semantic, dict):
        return _fail("missing semantic_index object")

    groups = semantic.get("groups")
    if not isinstance(groups, list) or not groups:
        return _fail("semantic_index.groups must be a non-empty list")

    reason = semantic.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        return _fail("semantic_index.reason must be a non-empty string")

    # ----------------------------
    # Validate groups structure
    # ----------------------------
    seen: List[int] = []

    for i, group in enumerate(groups):
        if not isinstance(group, list) or not group:
            return _fail(f"groups[{i}] must be a non-empty list")

        for idx in group:
            if not isinstance(idx, int):
                return _fail(f"groups[{i}] contains non-integer index")
            if idx < 0 or idx >= sentence_count:
                return _fail(
                    f"groups[{i}] contains invalid sentence index {idx}"
                )
            seen.append(idx)

    # ----------------------------
    # Each sentence must appear exactly once
    # ----------------------------
    expected = list(range(sentence_count))
    if sorted(seen) != expected:
        return _fail(
            f"semantic_index.groups must contain each sentence index exactly once. "
            f"Expected {expected}, got {sorted(seen)}"
        )

    # ----------------------------
    # Order must be preserved
    # ----------------------------
    if seen != sorted(seen):
        return _fail(
            "sentence indices must preserve original order across groups"
        )

    # ----------------------------
    # Safety block
    # ----------------------------
    safety = obj.get("safety")
    if not isinstance(safety, dict):
        return _fail("missing safety object")

    for key in (
        "adds_new_information",
        "removes_information",
        "medical_facts_changed",
    ):
        if key not in safety:
            return _fail(f"safety missing key: {key}")
        if safety[key] is not False:
            return _fail(f"safety.{key} must be false")

    return _ok(obj)
