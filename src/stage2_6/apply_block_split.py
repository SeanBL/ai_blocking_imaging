# stage2_6/apply_block_split.py
from __future__ import annotations

import copy
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


# -----------------------------
# Debug structure
# -----------------------------
@dataclass
class BlockSplitDebugItem:
    slide_id: str
    header: str
    action_taken: str
    new_slide_ids: List[str]
    reason: str


# -----------------------------
# Helpers (LOCKED)
# -----------------------------
def _get_slide_type(slide: Dict[str, Any]) -> str:
    return (
        slide.get("meta", {}).get("type")
        or slide.get("type")
        or ""
    ).lower()


def _get_header(slide):
    return (
        slide.get("meta", {}).get("header")
        or slide.get("header")
        or ""
    )


def _set_header(slide: Dict[str, Any], header: str) -> None:
    slide.setdefault("meta", {})["header"] = header


def _make_child_id(parent_id: str, index: int) -> str:
    return f"{parent_id}_b{index}"


def _get_content(slide: Dict[str, Any]) -> List[Any]:
    """
    Block split operates ONLY on list-based content.
    """
    content = slide.get("content")
    if not isinstance(content, list):
        raise ValueError("block_split requires slide['content'] to be a list.")
    return content


# -----------------------------
# Executor
# -----------------------------
def apply_block_split_executor(
    module: Dict[str, Any],
    routing_suggestions: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:

    slides_raw = module["slides"]
    suggestions = routing_suggestions.get("slides", {})

    # --------------------------------------------
    # Normalize slides (list or dict → ordered list)
    # --------------------------------------------
    if isinstance(slides_raw, dict):
        slide_items = list(slides_raw.items())
    elif isinstance(slides_raw, list):
        slide_items = []
        for idx, slide in enumerate(slides_raw):
            slide_id = (
                slide.get("meta", {}).get("id")
                or slide.get("id")
            )
            if not slide_id:
                raise ValueError(
                    f"Slide at index {idx} missing both meta.id and id"
                )

            slide_items.append((slide_id, slide))

    else:
        raise ValueError("module['slides'] must be list or dict")

    new_slides: OrderedDict[str, Dict[str, Any]] = OrderedDict()
    debug_items: List[BlockSplitDebugItem] = []

    for slide_id, slide in slide_items:

        header = _get_header(slide)

        # Non-panels pass through
        if _get_slide_type(slide) != "panel":
            new_slides[slide_id] = slide
            debug_items.append(
                BlockSplitDebugItem(
                    slide_id,
                    _get_header(slide),
                    "untouched",
                    [],
                    "non-panel",
                )
            )
            continue

        suggestion = suggestions.get(slide_id)

        # No block split requested → pass through
        if not suggestion or suggestion.get("routing") != "block_split":
            new_slides[slide_id] = slide
            debug_items.append(
                BlockSplitDebugItem(
                    slide_id,
                    _get_header(slide),
                    "untouched",
                    [],
                    "no block_split routing",
                )
            )
            continue

        groups = (
            suggestion
            .get("block_split", {})
            .get("groups")
        )

        if not isinstance(groups, list) or len(groups) < 2:
            new_slides[slide_id] = slide
            debug_items.append(
                BlockSplitDebugItem(
                    slide_id,
                    header,
                    "untouched",
                    [],
                    "block_split routing but insufficient groups",
                )
            )
            continue

        content = _get_content(slide)
        header = _get_header(slide)
        new_ids: List[str] = []

        for i, group in enumerate(groups, start=1):

            if not isinstance(group, list) or not group:
                raise ValueError(
                    f"[{slide_id}] Invalid block_split group at index {i-1}."
                )

            if max(group) >= len(content):
                raise ValueError(
                    f"[{slide_id}] block_split index out of range in group {group}."
                )

            child = copy.deepcopy(slide)
            child_id = _make_child_id(slide_id, i)

            child.setdefault("meta", {})["id"] = child_id
            _set_header(
                child,
                header if i == 1 else f"{header} (continued)"
            )

            child["content"] = [content[idx] for idx in group]

            new_slides[child_id] = child
            new_ids.append(child_id)

        debug_items.append(
            BlockSplitDebugItem(
                slide_id,
                header,
                "block_split",
                new_ids,
                f"split into {len(new_ids)} panels",
            )
        )

    # --------------------------------------------
    # Restore list-based slide output (Stage 2 shape)
    # --------------------------------------------
    new_module = {
        **module,
        "slides": list(new_slides.values())
    }

    debug_report = {
        "stage": "2.6",
        "action": "block_split",
        "items": [
            {
                "slide_id": d.slide_id,
                "header": d.header,
                "action_taken": d.action_taken,
                "new_slide_ids": d.new_slide_ids,
                "reason": d.reason,
            }
            for d in debug_items
        ],
    }

    return new_module, debug_report
