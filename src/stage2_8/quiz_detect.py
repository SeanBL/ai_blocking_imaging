from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .logger import logger


QUIZ_START_RE = re.compile(r"\[\[QUIZ:(\d+)\]\]")
QUIZ_INSERT_RE = re.compile(
    r"\[\[QUIZ:(\d+):QUESTIONS=(\d+),(\d+)(?:,(\d+))?\]\]"
)


@dataclass
class QuizState:
    quiz_id: int
    start_index: int
    insert_index: Optional[int] = None
    immediate_count: Optional[int] = None
    deferred_count: Optional[int] = None
    application_count: int = 1  # ✅ NEW (legacy default = 1)
    source_slide_indices: List[int] = field(default_factory=list)
    closed: bool = False


def _base_slide_id(slide_id: str) -> str:
    """
    Extract base slide id before Stage 2.5 split suffix.
    Example: stage2-017__p3 → stage2-017
    """
    return slide_id.split("__", 1)[0]


def detect_quizzes(slides: List[dict]) -> Dict[int, QuizState]:
    quizzes: Dict[int, QuizState] = {}

    # -------------------------------------------------
    # Pass 1: detect quiz markers
    # -------------------------------------------------
    for idx, slide in enumerate(slides):
        notes = slide.get("notes") or ""

        # -------------------------
        # QUIZ START
        # -------------------------
        for match in QUIZ_START_RE.finditer(notes):
            quiz_id = int(match.group(1))

            if quiz_id in quizzes:
                if quizzes[quiz_id].closed:
                    raise ValueError(
                        f"QUIZ:{quiz_id} start encountered after quiz was closed"
                    )
                # Duplicate start across split panels — safe to ignore
                continue

            quizzes[quiz_id] = QuizState(
                quiz_id=quiz_id,
                start_index=idx,
            )

        # -------------------------
        # QUIZ INSERT
        # -------------------------
        for match in QUIZ_INSERT_RE.finditer(notes):
            quiz_id = int(match.group(1))
            immediate = int(match.group(2))
            deferred = int(match.group(3))

            # Optional third value (application)
            if match.group(4) is not None:
                application = int(match.group(4))
            else:
                application = 1  # legacy default

            if quiz_id not in quizzes:
                raise ValueError(f"QUIZ:{quiz_id} insertion without start marker")

            if immediate == 0 and deferred == 0 and application == 0:
                raise ValueError(
                    f"QUIZ:{quiz_id} specifies zero questions (0,0,0)"
                )

            state = quizzes[quiz_id]
            state.insert_index = idx
            state.immediate_count = immediate
            state.deferred_count = deferred
            state.application_count = application
            state.closed = True

    # -------------------------------------------------
    # Pass 2: expand quiz scope across split panels
    # -------------------------------------------------
    for quiz_id, state in quizzes.items():
        if state.start_index is None or state.insert_index is None:
            continue

        # Base window: start → insert (inclusive)
        window_indices = list(range(state.start_index, state.insert_index + 1))

        # Collect base slide ids present in the window
        base_ids: set[str] = set()

        for i in window_indices:
            slide = slides[i]
            sid = slide.get("uuid") or slide.get("id")
            if sid:
                base_ids.add(_base_slide_id(sid))

        expanded_indices: List[int] = []

        for idx, slide in enumerate(slides):
            sid = slide.get("uuid") or slide.get("id")
            if not sid:
                continue

            if _base_slide_id(sid) in base_ids:
                expanded_indices.append(idx)

        expanded_indices = sorted(set(expanded_indices))

        state.source_slide_indices = expanded_indices

        logger.info(
            f"[Stage 2.8] QUIZ:{quiz_id} expanded source window — "
            f"slides={expanded_indices}"
        )

    # -------------------------------------------------
    # Final validation
    # -------------------------------------------------
    for quiz_id, state in quizzes.items():
        if not state.closed:
            raise ValueError(f"QUIZ:{quiz_id} start marker without QUESTIONS marker")

    return quizzes

