from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set

from .word_xml_extractors import extract_word_slide_text_fragments

def _extend_with_split_paragraphs(fragments: List[str], text: Any) -> None:
    """
    Stage 1 often stores multiple Word paragraphs joined with '\\n'.
    Word ground truth is paragraph-granular, so we must split to compare fairly.
    """
    if not text:
        return

    if not isinstance(text, str):
        text = str(text)

    # Split on newlines (preserve paragraph granularity)
    for part in text.splitlines():
        s = part.replace("\u00A0", " ")
        s = " ".join(s.split()).strip()
        if s:
            fragments.append(s)

# -------------------------------------------------
# Stage 1 JSON text extraction
# -------------------------------------------------

def extract_stage1_text_fragments(stage1_module: Dict[str, Any]) -> List[str]:
    """
    Extract ALL text that Stage 1 claims to preserve.

    This mirrors Stage 1's responsibility exactly:
    - headers
    - notes
    - image text
    - content.blocks paragraphs
    - bullets
    - engage1 intro + items
    - engage2 blocks + button_labels
    """

    fragments: List[str] = []

    slides = stage1_module.get("slides", [])
    if not isinstance(slides, list):
        return fragments

    for slide in slides:
        if not isinstance(slide, dict):
            continue

        # Header
        if slide.get("header"):
            _extend_with_split_paragraphs(fragments, slide["header"])

        # Notes
        if slide.get("notes"):
            _extend_with_split_paragraphs(fragments, slide["notes"])

        # Image
        if slide.get("image"):
            _extend_with_split_paragraphs(fragments, slide["image"])

        content = slide.get("content", {})

        # -------------------------
        # PANEL
        # -------------------------
        if slide.get("slide_type") == "panel":
            blocks = content.get("blocks", [])
            for b in blocks:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "paragraph":
                    fragments.append(b.get("text", ""))
                elif b.get("type") == "bullets":
                    fragments.extend(b.get("items", []))

        # -------------------------
        # ENGAGE 1
        # -------------------------
        if slide.get("slide_type") == "engage1":
            intro = content.get("intro", {})
            if isinstance(intro, dict):
                if intro.get("text"):
                    _extend_with_split_paragraphs(fragments, intro["text"])
                if intro.get("image"):
                    fragments.append(intro["image"])
                if intro.get("notes"):
                    fragments.append(intro["notes"])

            items = content.get("items", [])
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("button_label"):
                    fragments.append(item["button_label"])
                if item.get("image"):
                    fragments.append(item["image"])
                if item.get("notes"):
                    fragments.append(item["notes"])

                body = item.get("body", [])
                for b in body:
                    if b.get("type") == "paragraph":
                        fragments.append(b.get("text", ""))
                    elif b.get("type") == "bullets":
                        fragments.extend(b.get("items", []))

        # -------------------------
        # ENGAGE 2
        # -------------------------
        if slide.get("slide_type") == "engage2":
            labels = content.get("button_labels", [])
            fragments.extend(labels)

            blocks = content.get("blocks", [])
            for b in blocks:
                if b.get("type") == "paragraph":
                    fragments.append(b.get("text", ""))
                elif b.get("type") == "bullets":
                    fragments.extend(b.get("items", []))

    # Normalize whitespace here (simple + deterministic)
    out: List[str] = []
    for t in fragments:
        if not t:
            continue
        s = t.replace("\u00A0", " ")
        s = " ".join(s.split()).strip()
        if s:
            out.append(s)

    return out


# -------------------------------------------------
# Fidelity audit
# -------------------------------------------------

def run_stage1_fidelity_audit(
    *,
    docx_path: Path,
    stage1_module: Dict[str, Any],
) -> None:
    """
    HARD GATE.

    Ensures that every text fragment present in Word slide tables
    exists somewhere in Stage 1 output.

    Raises RuntimeError on failure.
    """

    word_fragments = extract_word_slide_text_fragments(docx_path)
    stage1_fragments = extract_stage1_text_fragments(stage1_module)

    word_set: Set[str] = set(word_fragments)
    stage1_set: Set[str] = set(stage1_fragments)

    missing = sorted(word_set - stage1_set)

    if missing:
        preview = "\n".join(f"- {m}" for m in missing[:10])
        raise RuntimeError(
            f"Stage 1 Fidelity Audit FAILED — {len(missing)} text fragment(s) missing.\n"
            f"First missing fragments:\n{preview}"
        )
