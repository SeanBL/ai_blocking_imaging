from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


QUIZ_START_RE = re.compile(r"\[\[QUIZ:(\d+)\]\]")
QUIZ_INSERT_RE = re.compile(r"\[\[QUIZ:(\d+):QUESTIONS=([\d]+),([\d]+)\]\]")


@dataclass
class QuizState:
    quiz_id: int
    start_index: int
    insert_index: Optional[int] = None
    immediate_count: Optional[int] = None
    deferred_count: Optional[int] = None
    source_slide_indices: List[int] = field(default_factory=list)
    closed: bool = False


def detect_quizzes(slides: List[dict]) -> Dict[int, QuizState]:
    quizzes: Dict[int, QuizState] = {}

    for idx, slide in enumerate(slides):
        notes = slide.get("notes") or ""

        # -------------------------
        # QUIZ START
        # -------------------------
        for match in QUIZ_START_RE.finditer(notes):
            quiz_id = int(match.group(1))

            if quiz_id in quizzes and not quizzes[quiz_id].closed:
                raise ValueError(f"QUIZ:{quiz_id} start encountered twice before closing")

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

            if quiz_id not in quizzes:
                raise ValueError(f"QUIZ:{quiz_id} insertion without start marker")

            if immediate == 0 and deferred == 0:
                raise ValueError(f"QUIZ:{quiz_id} specifies zero questions (0,0)")

            state = quizzes[quiz_id]
            state.insert_index = idx
            state.immediate_count = immediate
            state.deferred_count = deferred
            state.closed = True

    # -------------------------
    # Final validation
    # -------------------------
    for quiz_id, state in quizzes.items():
        if not state.closed:
            raise ValueError(f"QUIZ:{quiz_id} start marker without QUESTIONS marker")

    return quizzes
