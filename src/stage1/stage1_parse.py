from src.stage1.models import RawBlock, ParsedBlock
from dataclasses import dataclass
from typing import List

def parse_block(raw: RawBlock) -> ParsedBlock:
    """
    Parse a RawBlock into a structured ParsedBlock.
    Correct behavior for WiRED modules:
    - 'Image', 'English text', and 'Translation text' are ALWAYS template markers.
    - There is NEVER an actual image filename in the docx.
    - English text ALWAYS begins immediately after 'Translation text'.
    - If translation text is missing, English begins after 'English text'.
    """

    header_text = raw.header_line.replace("Header:", "").strip()

    english_text_paragraphs = []
    block_type_raw = None
    notes_raw = None

    collecting_english = False
    saw_english_label = False
    saw_translation_label = False

    for line in raw.lines:
        s = line.strip()

        # SECTION MARKERS
        if s.lower() == "image":
            continue

        if s.lower() == "english text":
            saw_english_label = True
            continue

        if s.lower() == "translation text":
            saw_translation_label = True
            collecting_english = True
            continue

        # NOTES
        if s.startswith("(") and s.endswith(")"):
            notes_raw = s
            continue

        if s.lower().startswith("matt:"):
            notes_raw = s
            continue

        if s == "CHANGE":
            notes_raw = "CHANGE"
            continue

        # ENGAGE MARKERS
        if s.lower() == "engage":
            block_type_raw = "engage"
            continue

        if s.lower() in ("engage2", "engage 2"):
            block_type_raw = "engage2"
            continue

        # FALLBACK: If there's no Translation text, start collecting after English text
        if saw_english_label and not saw_translation_label:
            collecting_english = True

        # COLLECT ENGLISH PARAGRAPHS
        if collecting_english and s != "":
            english_text_paragraphs.append(s)

    return ParsedBlock(
        header=header_text,
        image_raw=None,  # WiRED templates never contain real image names
        english_text_raw=english_text_paragraphs,
        block_type_raw=block_type_raw,
        notes_raw=notes_raw
    )