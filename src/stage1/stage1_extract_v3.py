"""
STAGE 1 INVARIANT CONTRACT (DO NOT VIOLATE)

Stage 1 is a STRUCTURAL extractor only.

INVARIANTS:
1. Paragraphs in Word are preserved as paragraphs in JSON.
2. Bulleted / numbered lists explicitly marked by Word are preserved as bullets.
3. Mixed prose + bullets in the same cell are preserved in order.
4. Stage 1 NEVER infers bullets, engages, or pedagogy.

If any invariant is broken, downstream stages become unreliable.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from docx import Document


def normalize(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.replace("\u00A0", " ").split()).strip()


def is_list_paragraph(p) -> bool:
    """
    True if Word explicitly marks this paragraph as a list item.
    Covers both styled lists and numbered/bulleted lists.
    """
    if p.style and p.style.name == "List Paragraph":
        return True

    pPr = p._p.pPr
    if pPr is not None and pPr.numPr is not None:
        return True

    return False


def canonical_col_label(raw: str) -> str:
    """
    Normalize table column headers so extraction is stable across
    variants like 'Notes and Instructions/Translations'.
    """
    t = normalize(raw).lower()

    if "/" in t:
        t = t.split("/", 1)[0].strip()

    if t.startswith("notes and instructions"):
        return "notes and instructions"
    if t.startswith("english text"):
        return "english text"
    if t.startswith("image"):
        return "image"
    if t.startswith("button labels"):
        return "button labels"

    return t

def is_slide_header(text: str) -> bool:
    """
    Detect slide header rows.
    Accepts:
      - 'Header: ...'
      - 'Header ...'
      - 'Slide (Header) ...'
      - 'Slide Header ...'
    """
    t = text.lower()
    return (
        t.startswith("header:")
        or t.startswith("header ")
        or t.startswith("slide (header)")
        or t.startswith("slide header")
    )

def extract_tables_v3(docx_path: Path) -> Dict[str, Any]:
    doc = Document(str(docx_path))

    module: Dict[str, Any] = {"module_title": docx_path.stem, "slides": []}
    slide_index = 0

    # Current slide state (persists across tables until a new slide header appears)
    slide: Optional[Dict[str, Any]] = None
    columns: Dict[str, List[str]] = {}
    col_labels: List[str] = []

    # Engage1 per-slide state
    engage1_mode = False
    engage1_intro_row_pending = False
    collecting_button_labels = False

    engage_intro_parts: List[str] = []
    engage_intro_image: Optional[str] = None
    engage_items: List[Dict[str, Any]] = []
    engage_intro_notes: List[str] = []

    def reset_engage1_state() -> None:
        nonlocal engage1_mode, engage1_intro_row_pending, collecting_button_labels
        nonlocal engage_intro_parts, engage_intro_image, engage_items, engage_intro_notes
        engage1_mode = False
        engage1_intro_row_pending = False
        collecting_button_labels = False
        engage_intro_parts = []
        engage_intro_image = None
        engage_items = []
        engage_intro_notes = []

    def finalize_slide(cur_slide: Dict[str, Any], cur_columns: Dict[str, List[str]]) -> None:
        """
        Convert collected column text into final slide JSON.
        IMPORTANT: Only Slide Type signals affect slide_type. Human prose notes do not.
        """
        nonlocal engage_items, engage_intro_parts, engage_intro_image, engage_intro_notes

        notes_parts: List[str] = []
        notes_parts.extend(cur_columns.get("notes and instructions", []))
        notes_parts.extend(cur_columns.get("notes and instructions__bullets", []))
        notes = "\n".join(notes_parts).strip()
        cur_slide["notes"] = notes if notes else ""

        notes_lower = notes.lower()
        if "slide type = engage 1" in notes_lower:
            cur_slide["slide_type"] = "engage1"
        elif "slide type = engage 2" in notes_lower:
            cur_slide["slide_type"] = "engage2"
        else:
            cur_slide["slide_type"] = "panel"

        # Slide-level image handling
        if cur_slide["slide_type"] == "engage1":
            cur_slide["image"] = None
        else:
            if "image" in cur_columns and cur_columns["image"]:
                img = " ".join(cur_columns["image"]).strip()
                cur_slide["image"] = img if img else None

        # -------------------------------
        # ENGAGE 1 output
        # -------------------------------
        if cur_slide["slide_type"] == "engage1":
            # bind button labels -> items in order
            labels: List[str] = []
            for txt in cur_columns.get("button labels", []):
                labels.extend([p.strip() for p in txt.split("|") if p.strip()])

            if labels:
                for i, item in enumerate(engage_items):
                    if i < len(labels):
                        item["button_label"] = labels[i]

            cur_slide["content"] = {
                "intro": {
                    "text": "\n".join(engage_intro_parts).strip(),
                    "image": engage_intro_image,
                    "notes": "\n".join(engage_intro_notes).strip() or None,
                },
                "items": engage_items,
            }
            return

        # -------------------------------
        # PANEL / ENGAGE2 output
        # -------------------------------
        blocks: List[Dict[str, Any]] = []
        for txt in cur_columns.get("english text", []):
            blocks.append({"type": "paragraph", "text": txt})

        bullet_items = cur_columns.get("english text__bullets", [])
        if bullet_items:
            blocks.append({"type": "bullets", "items": bullet_items})

        cur_slide["content"]["blocks"] = blocks

        if cur_slide["slide_type"] == "engage2":
            labels: List[str] = []
            for txt in cur_columns.get("button labels", []):
                labels.extend([p.strip() for p in txt.split("|") if p.strip()])
            if labels:
                cur_slide["content"]["button_labels"] = labels

    def start_new_slide(header_text: str, tbl, header_row_idx: int) -> None:
        """
        Finalize previous slide (if any), then initialize a new slide.
        """
        nonlocal slide, columns, col_labels, slide_index
        nonlocal engage1_mode, engage1_intro_row_pending, collecting_button_labels

        if slide is not None:
            finalize_slide(slide, columns)
            module["slides"].append(slide)

        slide_index += 1
        slide = {
            "id": f"slide_{slide_index:03d}",
            "header": header_text,
            "slide_type": "panel",
            "image": None,
            "notes": "",
            "content": {"blocks": []},
        }

        reset_engage1_state()

        # Next row is column label row
        label_row = tbl.rows[header_row_idx + 1]
        col_labels = [canonical_col_label(c.text) for c in label_row.cells]
        columns = {label: [] for label in col_labels if label}

    for tbl in doc.tables:
        if len(tbl.rows) < 3:
            continue

        row_idx = 0

        while row_idx < len(tbl.rows):
            row = tbl.rows[row_idx]
            first_cell = normalize(row.cells[0].text)
            first_lower = first_cell.lower()

            # -------------------------------
            # Start of slide
            # -------------------------------
            if is_slide_header(first_lower):
                start_new_slide(first_cell, tbl, row_idx)
                row_idx += 2
                continue

            # If we have not seen any slide yet, ignore stray tables
            if slide is None:
                row_idx += 1
                continue

            # -------------------------------
            # Build row-wise texts per column
            # -------------------------------
            row_texts: Dict[str, List[str]] = {}
            for idx, cell in enumerate(row.cells):
                if idx >= len(col_labels):
                    continue
                label = col_labels[idx]
                if not label:
                    continue
                texts = [normalize(p.text) for p in cell.paragraphs if normalize(p.text)]
                if texts:
                    row_texts[label] = texts

            img_texts = row_texts.get("image", [])
            eng_texts = row_texts.get("english text", [])
            notes_texts = row_texts.get("notes and instructions", [])

            # Always preserve notes at slide level
            if notes_texts:
                columns.setdefault("notes and instructions", []).extend(notes_texts)

            # -------------------------------
            # Engage1 detection (structural: Slide Type signal only)
            # -------------------------------
            if notes_texts:
                blob = " ".join(t.lower() for t in notes_texts)
                if "slide type = engage 1" in blob:
                    engage1_mode = True
                    engage1_intro_row_pending = True
                    collecting_button_labels = False

            # -------------------------------
            # ENGAGE 1 ROW-BASED PARSING
            # -------------------------------
            if engage1_mode:
                # Button Labels section starts when Image cell says "Button Labels"
                if img_texts and img_texts[0].strip().lower() == "button labels":
                    collecting_button_labels = True
                    if eng_texts:
                        columns.setdefault("button labels", []).extend(eng_texts)
                    row_idx += 1
                    continue

                if collecting_button_labels:
                    if eng_texts:
                        columns.setdefault("button labels", []).extend(eng_texts)
                    row_idx += 1
                    continue

                # Intro row: store intro image + intro text
                if engage1_intro_row_pending:
                    if img_texts:
                        engage_intro_image = " ".join(img_texts).strip() or engage_intro_image
                    if eng_texts:
                        engage_intro_parts.extend(eng_texts)
                    if notes_texts:
                        engage_intro_notes.extend(notes_texts)
                    engage1_intro_row_pending = False
                    row_idx += 1
                    continue

                # -------------------------------
                # ENGAGE 1 ITEM ROW (STRUCTURE-PRESERVING)
                # Preserves paragraphs + bullets in order
                # -------------------------------
                if eng_texts:
                    eng_blocks: List[Dict[str, Any]] = []

                    # Locate the English Text cell to re-inspect paragraph structure
                    try:
                        eng_col_idx = col_labels.index("english text")
                        eng_cell = row.cells[eng_col_idx]
                    except ValueError:
                        eng_cell = None

                    if eng_cell:
                        paras = [p for p in eng_cell.paragraphs if normalize(p.text)]

                        list_items: List[str] = []
                        for p in paras:
                            txt = normalize(p.text)
                            if not txt:
                                continue

                            if is_list_paragraph(p):
                                list_items.append(txt)
                            else:
                                if list_items:
                                    eng_blocks.append({
                                        "type": "bullets",
                                        "items": list_items,
                                    })
                                    list_items = []
                                eng_blocks.append({
                                    "type": "paragraph",
                                    "text": txt,
                                })

                        if list_items:
                            eng_blocks.append({
                                "type": "bullets",
                                "items": list_items,
                            })

                    item = {
                        "button_label": None,
                        "image": " ".join(img_texts).strip() if img_texts else None,
                        "body": eng_blocks,
                        "notes": "\n".join(notes_texts).strip() if notes_texts else None,
                    }

                    engage_items.append(item)
                    row_idx += 1
                    continue

            # -------------------------------
            # DEFAULT (NON-ENGAGE1) parsing: preserve bullets + prose
            # -------------------------------
            for idx, cell in enumerate(row.cells):
                if idx >= len(col_labels):
                    continue
                label = col_labels[idx]
                if not label:
                    continue

                paras = [p for p in cell.paragraphs if normalize(p.text)]
                if not paras:
                    continue

                list_items: List[str] = []
                non_list: List[str] = []
                for p in paras:
                    txt = normalize(p.text)
                    if is_list_paragraph(p):
                        list_items.append(txt)
                    else:
                        non_list.append(txt)

                if list_items:
                    if non_list:
                        columns[label].extend(non_list)
                    columns.setdefault(label + "__bullets", []).extend(list_items)
                    continue

                columns[label].extend(non_list)

            row_idx += 1

    # Finalize last slide once
    if slide is not None:
        finalize_slide(slide, columns)
        module["slides"].append(slide)

    return module


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Stage 1 v3 extractor (fixed bullets + no loss)")
    parser.add_argument("--in", dest="in_path", required=False)
    parser.add_argument("--out", dest="out_path", required=False)
    args = parser.parse_args()

    raw_dir = Path("data/raw")

    if not args.in_path:
        docx_files = list(raw_dir.glob("*.docx"))
        if len(docx_files) == 0:
            raise SystemExit("❌ No Word documents found in data/raw")
        if len(docx_files) > 1:
            raise SystemExit(f"❌ Multiple Word documents found in data/raw: {[f.name for f in docx_files]}")
        input_path = docx_files[0]
    else:
        input_path = Path(args.in_path)

    output_path = Path(args.out_path) if args.out_path else Path("data/processed/module_v3.json")

    module = extract_tables_v3(input_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(module, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Using input: {input_path.name}")
    print(f"✅ Output written to: {output_path}")
    print(f"✅ Extracted {len(module['slides'])} slides")


if __name__ == "__main__":
    main()

