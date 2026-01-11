from __future__ import annotations

from typing import Any, Dict, List, Tuple

RowTriple = Tuple[str, str, str]


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
    slide_type = (slide.get("slide_type") or slide.get("type") or "").lower()
    # print("DEBUG Stage3B slide_to_table_rows")
    # print("  slide_id:", slide.get("id"))
    # print("  slide_type:", slide_type)
    # print("  content keys:", list((slide.get("content") or {}).keys()))
    # print("  slide keys:", list(slide.keys()))
    slide_notes = slide.get("notes") or ""

    image = slide.get("image") or slide.get("image_path") or ""

    # 🔒 DISPATCH BY SLIDE TYPE ONLY

    if slide_type in ("engage", "engage1"):
        return _rows_for_engage(slide, image)

    if slide_type in ("engage2", "engage_2"):
        return _rows_for_engage2(slide, image)

    if slide_type == "quiz":
        return _rows_for_quiz(slide, image)

    # --- Panel default ---
    paras = _join_blocks_as_paragraphs(slide)
    return [(image, paras, slide_notes)]



def _rows_for_engage(slide: Dict[str, Any], image: str) -> List[RowTriple]:
    """
    Engage 1 mapping for FINAL Stage 2.9 schema.
    Engage fields live at the TOP LEVEL:
      slide["intro"]
      slide["items"]
    """
    rows: List[RowTriple] = []

    # --- Intro row ---
    intro = slide.get("intro") or {}
    intro_text = (intro.get("text") or "").strip()
    intro_image = intro.get("image") or image or ""
    intro_notes = slide.get("notes") or intro.get("notes") or "Slide Type = Engage 1"

    if intro_text:
        rows.append((intro_image, intro_text, intro_notes))

    # --- Item rows ---
    items = slide.get("items") or []
    for item in items:
        if not isinstance(item, dict):
            continue

        button = (item.get("button_label") or "").strip()

        body_blocks = item.get("body") or []
        body_texts = [
            b["text"].strip()
            for b in body_blocks
            if isinstance(b, dict) and b.get("text")
        ]
        body_text = "\n\n".join(body_texts)

        notes = f"Button Label: {button}" if button else ""
        rows.append(("", body_text, notes))

    return rows

def _rows_for_engage2(slide: Dict[str, Any], image: str) -> List[RowTriple]:
    """
    Engage2: intro + build steps; one shared button label.
    Expected possible shapes:
      page0["button_label"], page0["build"][i]["text"]
    """
    rows: List[RowTriple] = []

    pages = slide.get("pages") or []
    page0 = pages[0] if pages and isinstance(pages[0], dict) else {}

    btn = (page0.get("button_label") or page0.get("label") or "").strip()

    intro = page0.get("intro") or {}
    intro_text = (intro.get("text") or intro.get("title") or "").strip()
    if intro_text:
        rows.append((image, intro_text, f"Slide Type = Engage2 (Intro) | Button: {btn}" if btn else "Slide Type = Engage2 (Intro)"))
        image = ""

    build = page0.get("build") or page0.get("steps") or []
    for idx, step in enumerate(build, start=1):
        if not isinstance(step, dict):
            continue
        txt = (step.get("text") or step.get("body") or "").strip()
        notes = f"Step {idx} | Button Label: {btn}" if btn else f"Step {idx}"
        rows.append(("", txt, notes))

    if not rows:
        rows.append((image, "", slide.get("notes") or "Slide Type = Engage2"))


    return rows

def _rows_for_quiz(slide: Dict[str, Any], image: str) -> List[RowTriple]:
    """
    Stage 3B quiz rendering:
    One row per question.
    """
    rows: List[RowTriple] = []

    questions = slide.get("questions") or []
    slide_notes = slide.get("notes") or "Slide Type = Quiz"

    for q in questions:
        prompt = q.get("prompt", "").strip()

        # Build options text
        options = q.get("options") or {}
        option_lines = []
        for key in sorted(options.keys()):
            option_lines.append(f"{key}. {options[key]}")

        question_text = "\n\n".join(
            [prompt, *option_lines]
        ).strip()

        answer = q.get("correct_answer")
        rationale = q.get("rationale", "").strip()

        notes_parts = []
        if answer:
            notes_parts.append(f"Answer: {answer}")
        if rationale:
            notes_parts.append(rationale)

        notes_text = "\n\n".join(notes_parts)

        rows.append(("", question_text, notes_text))

    # Fallback if something went wrong
    if not rows:
        rows.append(("", "", slide_notes))

    return rows
