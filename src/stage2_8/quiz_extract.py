from __future__ import annotations

from typing import List, Dict, Any

from .quiz_detect import QuizState
from .logger import logger

def _index_sentence_annotations(sentence_annotations: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Stage 2.6 slides list into a dict keyed by slide uuid/id.
    """
    slides = sentence_annotations.get("slides")

    if not isinstance(slides, list):
        return {}

    index = {}
    for s in slides:
        slide_id = s.get("uuid") or s.get("id")
        if slide_id:
            index[slide_id] = s

    return index

def extract_quiz_source(
    *,
    slides: List[dict],
    quiz_state: QuizState,
    sentence_annotations: Dict[str, Any] | None = None,
) -> List[str]:

    if sentence_annotations is not None and not isinstance(sentence_annotations, dict):
        raise TypeError(
            f"sentence_annotations must be dict or None, got {type(sentence_annotations)}"
        )
    
    annotations_index: Dict[str, Any] = {}

    if isinstance(sentence_annotations, dict):
        annotations_index = _index_sentence_annotations(sentence_annotations)

    source_texts: List[str] = []
    included_slide_ids: List[str] = []

    # 🔒 SAFETY ASSERT — MUST HAVE SOURCE SLIDES
    assert quiz_state.source_slide_indices, (
        f"QUIZ:{quiz_state.quiz_id} has empty source_slide_indices"
    )

    for idx in quiz_state.source_slide_indices:

        slide = slides[idx]

        slide_id = slide.get("uuid") or slide.get("id") or f"(index:{idx})"
        slide_type = slide.get("type")

        included_slide_ids.append(slide_id)
        used_annotations = False

        # ---------------- PANEL — Tier 1 ----------------
        if slide_type == "panel" and annotations_index:
            ann = annotations_index.get(slide_id)
            if ann and "panels" in ann:
                for panel in ann["panels"]:
                    for sb in panel.get("sentence_blocks", []):
                        if "sentences" in sb:
                            for s in sb["sentences"]:
                                if isinstance(s, str) and s.strip():
                                    source_texts.append(s.strip())
                        elif sb.get("type") == "bullets":
                            for item in sb.get("items", []):
                                if isinstance(item, str) and item.strip():
                                    source_texts.append(item.strip())
                used_annotations = True

        # ---------------- PANEL — Tier 2 ----------------
        if slide_type == "panel" and not used_annotations:
            for block in slide.get("content", {}).get("blocks", []):
                if block.get("type") == "paragraph":
                    text = block.get("text", "").strip()
                    if text:
                        source_texts.append(text)
                elif block.get("type") == "bullets":
                    for item in block.get("items", []):
                        if isinstance(item, str) and item.strip():
                            source_texts.append(item.strip())

        # ---------------- ENGAGE ----------------
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