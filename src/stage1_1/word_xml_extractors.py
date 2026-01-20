from __future__ import annotations

import zipfile
import hashlib
from pathlib import Path
from typing import List, Set

from lxml import etree

def is_column_header_text(text: str) -> bool:
    return text.lower() in {
        "image",
        "english text",
        "notes and instructions",
        "button labels",
    }

# WordprocessingML namespace
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
}


# -------------------------------------------------
# Normalization (must match audit normalization)
# -------------------------------------------------

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\u00A0", " ")
    text = " ".join(text.split())
    return text.strip()


# -------------------------------------------------
# Slide header detection (MATCHES Stage 1)
# -------------------------------------------------

def is_slide_header_text(text: str) -> bool:
    t = text.lower()
    return (
        t.startswith("header:")
        or t.startswith("header ")
        or t.startswith("slide (header)")
        or t.startswith("slide header")
    )


# -------------------------------------------------
# XML helpers
# -------------------------------------------------

def paragraph_text(p: etree._Element) -> str:
    """
    Extract visible text from a <w:p> element.
    """
    texts = []
    for t in p.xpath(".//w:t", namespaces=NS):
        if t.text:
            texts.append(t.text)
    return normalize_text("".join(texts))


def xml_fingerprint(elem: etree._Element) -> str:
    """
    Create a stable hash of an XML element.
    This is how we dedupe Word's internal duplication.
    """
    raw = etree.tostring(elem, with_tail=False)
    return hashlib.sha256(raw).hexdigest()


# -------------------------------------------------
# Core extractor
# -------------------------------------------------

def extract_word_slide_text_fragments(docx_path: Path) -> List[str]:
    """
    DEFINITIVE Word text extractor.

    - Reads document.xml directly
    - Considers ONLY tables that contain slide headers
    - Extracts paragraph text from those tables
    - Deduplicates by XML identity
    """

    if not docx_path.exists():
        raise FileNotFoundError(docx_path)

    with zipfile.ZipFile(docx_path) as zf:
        xml_bytes = zf.read("word/document.xml")

    root = etree.fromstring(xml_bytes)

    fragments: List[str] = []
    seen_paragraphs: Set[str] = set()

    # Iterate tables
    for tbl in root.xpath(".//w:tbl", namespaces=NS):
        # Determine if this table is a slide table
        is_slide_table = False

        for p in tbl.xpath(".//w:tr/w:tc/w:p", namespaces=NS):
            txt = paragraph_text(p)
            if txt and is_slide_header_text(txt):
                is_slide_table = True
                break

        if not is_slide_table:
            continue

        # Extract paragraphs from slide tables
        for p in tbl.xpath(".//w:tr/w:tc/w:p", namespaces=NS):
            fp = xml_fingerprint(p)
            if fp in seen_paragraphs:
                continue
            seen_paragraphs.add(fp)

            txt = paragraph_text(p)
            if txt and not is_column_header_text(txt):
                fragments.append(txt)

    return fragments
