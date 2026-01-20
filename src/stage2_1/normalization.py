from __future__ import annotations

from typing import Iterable, List


# -----------------------------------------
# Normalization configuration (tunable)
# -----------------------------------------

# Minimum length (after normalization) for a fragment to be audited.
# This avoids false positives from trivial tokens like ".", "-", etc.
MIN_FRAGMENT_LENGTH = 5

# Whether to lowercase text before comparison.
# Keep False for now to stay maximally faithful.
LOWERCASE = False


# -----------------------------------------
# Core normalization
# -----------------------------------------

def normalize_text(text: str) -> str:
    """
    Canonical text normalization used by Stage 2.1.

    Rules (intentionally conservative):
    - Convert NBSP to space
    - Collapse all whitespace runs to single spaces
    - Strip leading/trailing whitespace
    - OPTIONAL lowercase (configurable)
    """
    if text is None:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # Normalize NBSP and whitespace
    s = text.replace("\u00A0", " ")
    s = " ".join(s.split())
    s = s.strip()

    if LOWERCASE:
        s = s.lower()

    return s


def is_meaningful_fragment(text: str) -> bool:
    """
    Determines whether a normalized fragment should be included
    in the fidelity audit.
    """
    if not text:
        return False
    return len(text) >= MIN_FRAGMENT_LENGTH


# -----------------------------------------
# Public helpers
# -----------------------------------------

def normalize_and_filter(
    fragments: Iterable[str],
) -> List[str]:
    """
    Normalize and filter an iterable of text fragments.

    Returns a list of normalized, meaningful fragments.
    Ordering is preserved (useful for diagnostics).
    """
    out: List[str] = []

    for raw in fragments:
        norm = normalize_text(raw)
        if is_meaningful_fragment(norm):
            out.append(norm)

    return out
