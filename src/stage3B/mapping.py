from __future__ import annotations

from typing import Any, Dict, List, Tuple

RowTriple = Tuple[str, str, str]

# (english_question, english_answer, translated_question, translated_answer)
QuizRow = Tuple[str, str, str, str]


def _join_blocks_as_paragraphs(slide: Dict[str, Any]) -> List[Tuple[str, bool]]:
    """
    Returns a list of (text, is_bullet) tuples.
    """
    content = slide.get("content") or {}
    blocks = content.get("blocks") or []

    out: List[Tuple[str, bool]] = []

    for b in blocks:
        if not isinstance(b, dict):
            continue

        btype = b.get("type")

        if btype == "paragraph":
            text = (b.get("text") or "").strip()
            if text:
                out.append((text, False))

        elif btype == "bullets":
            for item in b.get("items", []):
                if item:
                    out.append((str(item).strip(), True))

    return out


def slide_to_table_rows(slide: Dict[str, Any]) -> List[RowTriple]:
    """
    Returns list of (image, english, notes) rows for this slide.
    Deterministic; no mutation.
    """
    raw_type = (slide.get("slide_type") or slide.get("type") or "").lower()
    notes = (slide.get("notes") or "").lower()

    if "slide type = engage 2" in notes:
        slide_type = "engage2"
    elif "slide type = engage 1" in notes:
        slide_type = "engage1"
    else:
        slide_type = raw_type
    slide_notes = slide.get("notes") or ""

    image = slide.get("image") or slide.get("image_path") or ""

    # 🔒 DISPATCH BY SLIDE TYPE ONLY
    if slide_type in ("engage2", "engage_2"):
        return _rows_for_engage2(slide, image)

    if slide_type in ("engage", "engage1"):
        return _rows_for_engage(slide, image)

    if slide_type == "quiz":
        return _rows_for_quiz(slide)

    # --- Panel default ---
    paras = _join_blocks_as_paragraphs(slide)
    return [(image, paras, slide_notes)]


def _coerce_body_blocks(item: Dict[str, Any]) -> List[Any]:
    """
    Engage item bodies appear in a few deterministic shapes across the pipeline.
    This function ONLY normalizes how we READ them for Stage 3B rendering.
    No schema changes, no inference.
    """
    # Most common: item["body"] is a list of dicts like {"type":"paragraph","text":"..."}
    body = item.get("body")
    if isinstance(body, list):
        return body

    # Sometimes: item["body"] may be a dict wrapping blocks
    if isinstance(body, dict):
        blocks = body.get("blocks")
        if isinstance(blocks, list):
            return blocks

    # Sometimes: item["content"]["blocks"]
    content = item.get("content")
    if isinstance(content, dict):
        blocks = content.get("blocks")
        if isinstance(blocks, list):
            return blocks

    return []


def _render_body_blocks_to_text(body_blocks: List[Any]) -> str:
    """
    Render engage body blocks into a single English text string.
    Supports paragraphs AND bullets.
    Deterministic, render-only.
    """
    parts: List[str] = []

    for b in body_blocks:
        if not isinstance(b, dict):
            continue

        btype = b.get("type")

        if btype == "paragraph":
            txt = (b.get("text") or "").strip()
            if txt:
                parts.append(txt)

        elif btype == "bullets":
            for item in b.get("items", []):
                if item:
                    parts.append(f"• {str(item).strip()}")

    return "\n\n".join(parts).strip()



def _rows_for_engage(slide: Dict[str, Any], image: str) -> List[RowTriple]:
    """
    Engage 1 mapping for FINAL Stage 2 schema.

    REQUIRED Stage 3B behavior (per your spec):
      - Engage intro is rendered.
      - Engage items are rendered in exact order; none dropped.
      - Button labels MUST appear under the English Text column (NOT notes).
      - Button labels should be visually grouped with the corresponding engage item content.
      - Notes column: intro row may contain slide notes; item rows should NOT misuse notes for button labels.
    """
    rows: List[RowTriple] = []

    slide_notes = slide.get("notes") or ""

    # Stage 2 schema: intro/items live under slide["content"]
    content = slide.get("content") or {}

    # --- Intro row ---
    intro = content.get("intro") or slide.get("intro") or {}
    intro_text = (intro.get("text") or "").strip()
    intro_image = intro.get("image") or image or ""

    # Put slide notes on intro row only (deterministic, render-only)
    if intro_text:
        rows.append((intro_image, intro_text, slide_notes))
        # After intro image used once, clear for subsequent rows
        image = ""

    # --- Item rows (preserve order, no drops) ---
    items = content.get("items") or slide.get("items") or []

    content_texts: List[str] = []
    button_texts: List[str] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        button = (item.get("button_label") or "").strip()

        # Legacy Engage-1 button items encoded as image == "Button Label"
        if not button and item.get("image") == "Button Label":
            body_blocks = _coerce_body_blocks(item)
            button = _render_body_blocks_to_text(body_blocks)

        body_blocks = _coerce_body_blocks(item)
        body_text = _render_body_blocks_to_text(body_blocks)

        # Content item (always render body text when present)
        if body_text:
            content_texts.append(body_text)

        # Button item (render button whenever button_label exists OR legacy encoding)
        if button:
            button_texts.append(f"[Button] {button}")


    # Emit content rows first
    for txt in content_texts:
        rows.append(("", txt, ""))

    # Emit button rows last (each in its own cell)
    for btn in button_texts:
        rows.append(("", btn, ""))

    # Defensive fallback: if intro missing and items empty, still emit one deterministic row.
    if not rows:
        rows.append((image, "", slide_notes))

    return rows


def _rows_for_engage2(slide: Dict[str, Any], image: str) -> List[RowTriple]:
    """
    Engage 2 mapping (FINAL, render-only).

    Expected canonical shape:
      - slide["build"] : list of steps
      - step["content"] : list[str]
      - slide["button_labels"] : list[str]
    """
    rows: List[RowTriple] = []

    slide_notes = slide.get("notes") or ""

    # --- Build list (primary Engage 2 content) ---
    build = slide.get("build") or []

    first_row = True

    for step in build:
        if not isinstance(step, dict):
            continue

        contents = step.get("content") or []
        if not isinstance(contents, list):
            continue

        for text in contents:
            txt = str(text).strip()
            if not txt:
                continue

            if first_row:
                rows.append((image, txt, slide_notes))
                image = ""
                first_row = False
            else:
                rows.append(("", txt, ""))

    # --- Button labels (after all build items) ---
    button_labels = slide.get("button_labels") or []
    for lbl in button_labels:
        t = str(lbl).strip()
        if t:
            rows.append(("", f"[Button] {t}", ""))

    # Defensive fallback
    if not rows:
        rows.append((image, "", slide_notes))

    return rows

def _rows_for_quiz(slide: Dict[str, Any]) -> List[QuizRow]:
    """
    Quiz rows:
    (English Question, English Answer, Translated Question, Translated Answer)
    """
    rows: List[QuizRow] = []

    questions = slide.get("questions") or []

    for q in questions:
        prompt = q.get("prompt", "").strip()

        options = q.get("options") or {}
        option_lines = [f"{k}. {options[k]}" for k in sorted(options.keys())]

        english_question = "\n\n".join([prompt, *option_lines]).strip()

        answer = q.get("correct_answer", "")
        rationale = q.get("rationale", "").strip()

        english_answer = f"Answer: {answer}"
        if rationale:
            english_answer += f"\n\n{rationale}"

        rows.append(
            (
                english_question,
                english_answer,
                "",  # translated question (future)
                "",  # translated answer (future)
            )
        )

    return rows

