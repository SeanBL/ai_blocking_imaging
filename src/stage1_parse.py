from stage1_extract import RawBlock
from dataclasses import dataclass
from typing import List


@dataclass
class ParsedBlock:
    header: str
    image_raw: str | None
    english_text_raw: List[str]     # List of paragraphs
    block_type_raw: str | None      # "engage", "engage2", or None
    notes_raw: str | None


def parse_block(raw: RawBlock) -> ParsedBlock:
    """
    Turn a RawBlock (header + raw lines) into a structured ParsedBlock.
    Produces english_text_raw as a list of paragraphs.
    Uses enhanced logic:
    - If 'Translation text' exists → English begins after it.
    - If 'Translation text' is missing → English begins after 'English text'.
    """
    
    header_text = raw.header_line.replace("Header:", "").strip()
    
    image_raw = None
    english_text_paragraphs = []
    block_type_raw = None
    notes_raw = None

    # State machine flags
    saw_image_label = False
    saw_english_label = False
    saw_translation_label = False
    collecting_english = False

    for line in raw.lines:
        s = line.strip()

        # --- Section Labels ---
        if s.lower() == "image":
            saw_image_label = True
            collecting_english = False
            continue

        if s.lower() == "english text":
            saw_english_label = True
            # Do NOT start collecting until we know if Translation text exists
            collecting_english = False
            continue

        if s.lower() == "translation text":
            saw_translation_label = True
            # English text begins after this
            collecting_english = True
            continue

        # --- Engage Markers ---
        if s.lower() == "engage":
            block_type_raw = "engage"
            continue

        if s.lower() in ("engage2", "engage 2"):
            block_type_raw = "engage2"
            continue

        # --- Editor Notes ---
        if s.startswith("(") and s.endswith(")"):
            # e.g. (Technical note)
            notes_raw = s
            continue

        if s.lower().startswith("matt:"):
            notes_raw = s
            continue

        if s == "CHANGE":
            notes_raw = "CHANGE"
            continue

        # --- Image reference ---
        if saw_image_label and image_raw is None and s not in ("",):
            image_raw = s
            continue

        # --- Optional enhancement ---
        # If we saw "English text" but NEVER saw "Translation text"
        # then English text begins immediately after "English text"
        if saw_english_label and not saw_translation_label:
            # If we encounter the first non-empty line after English text
            if s not in ("",) and not collecting_english:
                collecting_english = True

        # --- Collect English paragraphs ---
        if collecting_english:
            if s not in ("",):
                english_text_paragraphs.append(s)

    return ParsedBlock(
        header=header_text,
        image_raw=image_raw,
        english_text_raw=english_text_paragraphs,
        block_type_raw=block_type_raw,
        notes_raw=notes_raw
    )