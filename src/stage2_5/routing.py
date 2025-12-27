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
    if slide.get("type") != "panel":
        return PanelRouting.NO_ACTION

    blocks = slide.get("content", {}).get("blocks", [])
    if not blocks:
        return PanelRouting.NO_ACTION

    # Bullet-aware routing
    paragraph_blocks = [b for b in blocks if b.get("type") == "paragraph"]
    bullet_blocks = [b for b in blocks if b.get("type") == "bullets"]

    # If bullets exist, decide based on paragraph count
    if bullet_blocks:
        # One paragraph + bullets → keep together
        if len(paragraph_blocks) <= 1:
            return PanelRouting.NO_ACTION

        # Multiple paragraphs + bullets → structural split
        return PanelRouting.BLOCK_SPLIT


    # Multiple paragraph blocks
    if len(blocks) > 1:
        total_words = sum(word_count(b["text"]) for b in blocks if b["type"] == "paragraph")

        if total_words <= 140:
            return PanelRouting.BLOCK_SPLIT

        return PanelRouting.SEMANTIC_INDEX

    # Single paragraph
    block = blocks[0]
    if block["type"] == "paragraph" and word_count(block["text"]) > 70:
        return PanelRouting.SEMANTIC_SPLIT

    return PanelRouting.NO_ACTION



def has_bullets(blocks: list[dict]) -> bool:
    return any(block.get("type") == "bullets" for block in blocks)

