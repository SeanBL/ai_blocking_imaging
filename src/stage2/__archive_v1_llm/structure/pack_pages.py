from __future__ import annotations
from typing import List, Dict, Any


TARGET_MIN = 35
TARGET_MAX = 70
HARD_MAX = 80


def _word_count(text: str) -> int:
    return len(text.split())


def pack_paragraphs(
    paragraph_indices: List[int],
    paragraphs: List[str],
) -> List[Dict[str, Any]]:
    """
    Deterministically pack paragraphs into pages.
    """
    pages = []
    current = []
    current_wc = 0

    for idx in paragraph_indices:
        wc = _word_count(paragraphs[idx])

        if current and current_wc + wc > HARD_MAX:
            pages.append({"paragraph_indices": current})
            current = [idx]
            current_wc = wc
        else:
            current.append(idx)
            current_wc += wc

            if current_wc >= TARGET_MIN:
                pages.append({"paragraph_indices": current})
                current = []
                current_wc = 0

    if current:
        pages.append({"paragraph_indices": current})

    return pages
