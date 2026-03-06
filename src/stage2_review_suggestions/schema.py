from __future__ import annotations
from typing import TypedDict, List, Optional, Literal


BlockType = Literal[
    "paragraph",
    "bullets",
    "engage_item",
    "engage_intro_proposed",   # NEW
]


class ReviewBlock(TypedDict):
    block_id: str
    type: BlockType
    original: Optional[str]   # allow None for proposed intros
    suggested: Optional[str]
    notes: Optional[str]


class ReviewSlide(TypedDict):
    slide_id: str
    slide_type: str
    blocks: List[ReviewBlock]


class ReviewPayload(TypedDict):
    review_version: str
    source_stage: str
    slides: List[ReviewSlide]

