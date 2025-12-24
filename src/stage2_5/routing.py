# src/stage2_5/routing.py

from enum import Enum
from typing import Dict, Any

from .validators import word_count


class PanelRouting(str, Enum):
    NO_ACTION = "no_action"
    BLOCK_SPLIT = "block_split"        # structural (writer lumped slides)
    SEMANTIC_SPLIT = "semantic_split"  # one long paragraph
    SEMANTIC_INDEX = "semantic_index"  # multiple logical ideas, needs reasoning


def classify_panel(slide: Dict[str, Any]) -> PanelRouting:
    """
    Routing rules (ordered, intentional):

    1. Non-panels → NO_ACTION
    2. Panels with bullets → NO_ACTION (never touch bullets)
    3. Multiple content blocks:
        - If blocks are short → BLOCK_SPLIT
        - If blocks are long → SEMANTIC_INDEX
    4. Single overlong paragraph → SEMANTIC_SPLIT
    """

    if slide.get("type") != "panel":
        return PanelRouting.NO_ACTION

    content = slide.get("content", [])
    if not content:
        return PanelRouting.NO_ACTION

    # Never touch bullet-based panels
    if any(has_bullets(block) for block in content):
        return PanelRouting.NO_ACTION

    # Multiple blocks: decide structural vs semantic
    if len(content) > 1:
        total_words = sum(word_count(b) for b in content)

        # Writer clearly lumped slides together
        if total_words <= 140:
            return PanelRouting.BLOCK_SPLIT

        # Multiple large ideas → needs semantic reasoning
        return PanelRouting.SEMANTIC_INDEX

    # Exactly one block from here
    text = content[0]

    # Single long paragraph → semantic split
    if word_count(text) > 70:
        return PanelRouting.SEMANTIC_SPLIT

    return PanelRouting.NO_ACTION


def has_bullets(text: str) -> bool:
    return any(
        line.strip().startswith(("•", "-", "*"))
        for line in text.splitlines()
    )
