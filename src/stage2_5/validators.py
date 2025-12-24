# src/stage2_5/validators.py

import re
from typing import List

SENTENCE_SPLIT_REGEX = re.compile(r"[.!?]+")


def word_count(text: str) -> int:
    return len(text.split())


def sentence_count(text: str) -> int:
    return len([s for s in SENTENCE_SPLIT_REGEX.split(text) if s.strip()])


def panel_needs_split(panel_text: str) -> bool:
    """
    Structural rule:
    Panels > 70 words may need to be split into multiple panels.
    """
    return word_count(panel_text) > 70


def panel_needs_sentence_reflow(panel_text: str) -> bool:
    """
    Readability rule:
    Any panel may benefit from sentence reflow
    if it exceeds 2–3 sentences.
    """
    return sentence_count(panel_text) > 3


def engage_item_exceeds_soft_limit(text: str) -> bool:
    return word_count(text) > 50


def engage_item_exceeds_hard_limit(text: str) -> bool:
    return word_count(text) > 70


def button_label_invalid(label: str) -> bool:
    """
    Button labels must be ≤ 4 words, no punctuation.
    """
    if not label:
        return True
    if word_count(label) > 4:
        return True
    if re.search(r"[^\w\s]", label):
        return True
    return False
