from __future__ import annotations

from typing import List

from .quiz_detect import QuizState
from .logger import logger


def extract_quiz_source(
    slides: List[dict],
    quiz_state: QuizState,
) -> List[str]:
    """
    Extract instructional text for a quiz.

    CONTRACT:
    - EVERYTHING inside slide.content is included
    - Panels + all Engage content
    """

    source_texts: List[str] = []
    included_slide_ids: List[str] = []

    for idx in range(quiz_state.start_index, quiz_state.insert_index + 1):
        slide = slides[idx]

        # ✅ CANONICAL STAGE 2.5 KEYS
        slide_id = slide.get("uuid", f"(index:{idx})")
        slide_type = slide.get("type")

        included_slide_ids.append(slide_id)

        # -----------------------------
        # PANEL
        # -----------------------------
        if slide_type == "panel":
            for block in slide.get("content", {}).get("blocks", []):
                if block.get("type") == "paragraph":
                    text = block.get("text", "").strip()
                    if text:
                        source_texts.append(text)

                elif block.get("type") == "bullets":
                    for item in block.get("items", []):
                        if isinstance(item, str) and item.strip():
                            source_texts.append(item.strip())

        # -----------------------------
        # ENGAGE (ALL)
        # -----------------------------
        elif slide_type in ("engage", "engage1", "engage2"):
            intro = slide.get("intro")
            if intro and intro.get("text"):
                source_texts.append(intro["text"].strip())

            for item in slide.get("items", []):
                for body_block in item.get("body", []):
                    if body_block.get("type") == "paragraph":
                        text = body_block.get("text", "").strip()
                        if text:
                            source_texts.append(text)

                    elif body_block.get("type") == "bullets":
                        for bullet in body_block.get("items", []):
                            if isinstance(bullet, str) and bullet.strip():
                                source_texts.append(bullet.strip())

    logger.info(
        f"Stage 2.8 QUIZ:{quiz_state.quiz_id} source window slides: {included_slide_ids}"
    )
    logger.info(
        f"Stage 2.8 QUIZ:{quiz_state.quiz_id} extracted text blocks: {len(source_texts)}"
    )

    if not source_texts:
        raise ValueError(
            f"QUIZ:{quiz_state.quiz_id} has no instructional content in the inclusive window"
        )

    return source_texts

