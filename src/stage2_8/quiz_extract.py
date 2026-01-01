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

    ✅ INCLUDED (window is INCLUSIVE):
      - Start marker slide (index = start_index)
      - All slides between
      - QUESTIONS marker slide (index = insert_index)

    ✅ INCLUDED content types:
      - Panel slide paragraph text
      - Engage slide intro + item content

    ❌ EXCLUDED:
      - Button labels
      - Images
      - Notes/markers (we never read notes here anyway)
    """

    source_paragraphs: List[str] = []
    included_slide_ids: List[str] = []

    # INCLUSIVE window
    for idx in range(quiz_state.start_index, quiz_state.insert_index + 1):
        slide = slides[idx]
        slide_id = slide.get("id", f"(index:{idx})")
        included_slide_ids.append(slide_id)

        slide_type = slide.get("slide_type")

        # -----------------------------
        # PANEL slides
        # -----------------------------
        if slide_type == "panel":
            blocks = slide.get("content", {}).get("blocks", [])
            for block in blocks:
                if block.get("type") == "paragraph":
                    text = block.get("text", "").strip()
                    if text:
                        source_paragraphs.append(text)

        # -----------------------------
        # ENGAGE slides
        # -----------------------------
        elif slide_type == "engage":
            # Intro content
            intro = slide.get("intro", {})
            intro_content = intro.get("content", [])
            if isinstance(intro_content, list):
                for text in intro_content:
                    if isinstance(text, str) and text.strip():
                        source_paragraphs.append(text.strip())

            # Item content
            for item in slide.get("items", []):
                item_content = item.get("content", [])
                if isinstance(item_content, list):
                    for text in item_content:
                        if isinstance(text, str) and text.strip():
                            source_paragraphs.append(text.strip())

        # other slide types intentionally ignored

    # Debug visibility (you explicitly requested this)
    logger.info(
        f"Stage 2.8 QUIZ:{quiz_state.quiz_id} source window slides: {included_slide_ids}"
    )
    logger.info(
        f"Stage 2.8 QUIZ:{quiz_state.quiz_id} extracted paragraphs: {len(source_paragraphs)}"
    )

    if not source_paragraphs:
        raise ValueError(
            f"QUIZ:{quiz_state.quiz_id} has no instructional content in the inclusive window"
        )

    return source_paragraphs

