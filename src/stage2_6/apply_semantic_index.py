# stage2_6/apply_semantic_index.py
from __future__ import annotations

import copy
import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


# -----------------------------
# Debug structures
# -----------------------------
@dataclass
class SplitDebugItem:
    slide_id: str
    header: str
    original_word_count: int
    action_taken: str
    new_slide_ids: List[str]
    reason: str


# -----------------------------
# Helpers (LOCKED CONTRACT)
# -----------------------------
def _get_slide_header(slide: Dict[str, Any]) -> str:
    return (
        slide.get("meta", {}).get("header")
        or slide.get("header")
        or ""
    )


def _set_slide_header(slide: Dict[str, Any], header: str) -> None:
    slide.setdefault("meta", {})["header"] = header


def _get_slide_type(slide: Dict[str, Any]) -> str:
    return (
        slide.get("meta", {}).get("type")
        or slide.get("type")
        or ""
    ).lower()


def _get_panel_text(slide: Dict[str, Any]) -> str:
    content = slide.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(content)
    raise ValueError("Panel missing authoritative 'content' field.")


def _set_panel_text_like_original(
    new_slide: Dict[str, Any],
    original_slide: Dict[str, Any],
    sliced_text: str,
) -> None:
    if isinstance(original_slide.get("content"), list):
        new_slide["content"] = [sliced_text]
    else:
        new_slide["content"] = sliced_text


def _word_count(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def _make_child_slide_id(parent_id: str, index: int) -> str:
    return f"{parent_id}_p{index}"


# -----------------------------
# Main executor
# -----------------------------
def apply_semantic_index_executor(
    module_stage2: Dict[str, Any],
    routing_suggestions: Dict[str, Any],
    *,
    max_words: int = 70,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:

    slides_raw = module_stage2["slides"]

    if isinstance(slides_raw, dict):
        slide_items = list(slides_raw.items())
    elif isinstance(slides_raw, list):
        slide_items = []
        for idx, slide in enumerate(slides_raw):
            slide_id = slide.get("meta", {}).get("id") or slide.get("id")
            if not slide_id:
                raise ValueError(
                    f"Slide at index {idx} missing both meta.id and id"
                )
            slide_items.append((slide_id, slide))
    else:
        raise ValueError("module_stage2['slides'] must be dict or list")

    suggestions = routing_suggestions.get("slides", {})

    new_slides: OrderedDict[str, Dict[str, Any]] = OrderedDict()
    debug_items: List[SplitDebugItem] = []

    for slide_id, slide in slide_items:
        suggestion = suggestions.get(slide_id, {}) 
        slide_type = _get_slide_type(slide)
        header = _get_slide_header(slide)

        # Non-panels untouched
        if slide_type != "panel":
            new_slides[slide_id] = slide
            debug_items.append(
                SplitDebugItem(
                    slide_id,
                    header,
                    0,
                    "untouched",
                    [],
                    "non-panel",
                )
            )
            continue

        panel_text = _get_panel_text(slide)
        wc = _word_count(panel_text)

        # <=70 words untouched
        if wc <= max_words:
            new_slides[slide_id] = slide
            debug_items.append(
                SplitDebugItem(
                    slide_id,
                    header,
                    wc,
                    "untouched",
                    [],
                    "<=70 words",
                )
            )
            continue

        # >70 words — attempt semantic split ONLY if boundaries exist
        suggestion = suggestions.get(slide_id, {})

        indexes = (
            suggestion
            .get("strict_sentence_boundaries", {})
            .get("sentence_reflow", {})
            .get("indexes")
        )

        # 🔒 OPTION A FIX — NO BOUNDARIES → DO NOT SPLIT
        if not isinstance(indexes, list) or len(indexes) < 3:
            new_slides[slide_id] = slide
            debug_items.append(
                SplitDebugItem(
                    slide_id,
                    header,
                    wc,
                    "untouched",
                    [],
                    ">70 words but no sentence boundaries (e.g., bullets)",
                )
            )
            continue

        # Build sentence spans
        sentence_spans = [
            (indexes[i], indexes[i + 1])
            for i in range(len(indexes) - 1)
        ]

        new_ids: List[str] = []
        current_start = None
        current_end = None
        current_wc = 0
        slide_index = 1

        def emit_chunk(start: int, end: int, idx: int):
            chunk_text = panel_text[start:end].strip()
            wc = _word_count(chunk_text)

            # 🔒 NEW — HARD FLOOR
            if wc < 30:
                raise ValueError(
                    f"[{slide_id}] Invalid chunk <30 words ({wc}). Refusing to emit."
                )

            # 🔒 NEW — HARD CEILING
            if wc > max_words:
                raise ValueError(
                    f"[{slide_id}] Invalid chunk >{max_words} words ({wc}). Refusing to emit."
                )

            child = copy.deepcopy(slide)
            child_id = _make_child_slide_id(slide_id, idx)

            child.setdefault("meta", {})["id"] = child_id
            _set_slide_header(
                child,
                header if idx == 1 else f"{header} (continued)"
            )

            _set_panel_text_like_original(child, slide, chunk_text)
            new_slides[child_id] = child
            new_ids.append(child_id)


        for start, end in sentence_spans:
            sentence_text = panel_text[start:end]
            sentence_wc = _word_count(sentence_text)

            if current_start is None:
                current_start = start
                current_end = end
                current_wc = sentence_wc
                continue

            # Accumulate while under limit
            if current_wc + sentence_wc <= max_words:
                current_end = end
                current_wc += sentence_wc
            else:
                emit_chunk(current_start, current_end, slide_index)
                slide_index += 1

                current_start = start
                current_end = end
                current_wc = sentence_wc

        # Emit final chunk
        if current_start is not None:
            emit_chunk(current_start, current_end, slide_index)

        # 🔒 HARD GUARANTEE — MUST BE AFTER ALL CHUNKS ARE EMITTED
        # This MUST be outside the loop, but INSIDE the semantic-split path
        if len(new_ids) < 2:
            raise ValueError(
                f"[{slide_id}] >{max_words} words but produced only {len(new_ids)} slide(s)."
            )

        debug_items.append(
            SplitDebugItem(
                slide_id,
                header,
                wc,
                "semantic_split",
                new_ids,
                f">{max_words} words",
            )
        )

    new_module = {
        **module_stage2,
        "slides": list(new_slides.values())
    }

    debug_report = {
        "stage": "2.6",
        "action": "apply_semantic_index",
        "items": [
            {
                "slide_id": d.slide_id,
                "header": d.header,
                "original_word_count": d.original_word_count,
                "action_taken": d.action_taken,
                "new_slide_ids": d.new_slide_ids,
                "reason": d.reason,
            }
            for d in debug_items
        ],
    }

    return new_module, debug_report

