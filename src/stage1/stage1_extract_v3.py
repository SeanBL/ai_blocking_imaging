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
from typing import Dict, List, Any

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

    return t


def extract_tables_v3(docx_path: Path) -> Dict[str, Any]:
    doc = Document(str(docx_path))

    module = {"module_title": docx_path.stem, "slides": []}
    slide_index = 0

    # Engage1 per-slide state (reset when new slide starts)
    engage1_mode = False
    engage1_intro_row_pending = False
    collecting_button_labels = False
    engage1_single_image_mode = False

    engage_intro_parts: List[str] = []
    engage_intro_image: str | None = None
    engage_items: List[Dict[str, Any]] = []
    engage_intro_notes: List[str] = []


    def finalize_slide(slide, columns):
        notes_parts: List[str] = []
        notes_parts.extend(columns.get("notes and instructions", []))
        notes_parts.extend(columns.get("notes and instructions__bullets", []))
        notes = "\n".join(notes_parts).strip()
        slide["notes"] = notes

        notes_lower = notes.lower()
        if "slide type = engage 1" in notes_lower:
            slide["slide_type"] = "engage1"
        elif "slide type = engage 2" in notes_lower:
            slide["slide_type"] = "engage2"
        else:
            slide["slide_type"] = "panel"

        # Only suppress slide-level image for Engage1
        if slide["slide_type"] == "engage1":
            slide["image"] = None
        else:
            # Preserve normal panel images (existing Stage 1 behavior)
            if "image" in columns and columns["image"]:
                img = " ".join(columns["image"]).strip()
                slide["image"] = img if img else None

        # -------------------------------
        # ENGAGE 1 output (ROW-BASED, FROM INSPECTION OUTPUT)
        # -------------------------------
        if slide["slide_type"] == "engage1":
            # bind button labels -> items in order
            labels: List[str] = []
            for txt in columns.get("button labels", []):
                # your docs show one label per row, but we allow pipes too
                labels.extend([p.strip() for p in txt.split("|") if p.strip()])

            if labels:
                for i, item in enumerate(engage_items):
                    if i < len(labels):
                        item["button_label"] = labels[i]

            slide["content"] = {
                "intro": {
                    "text": "\n".join(engage_intro_parts).strip(),
                    "image": engage_intro_image,
                    "notes": "\n".join(engage_intro_notes).strip() or None,
                },
                "items": engage_items,
            }
            return  # DO NOT fall through

        # -------------------------------
        # PANEL / other types output (existing behavior)
        # -------------------------------
        blocks = []
        for txt in columns.get("english text", []):
            blocks.append({"type": "paragraph", "text": txt})

        bullet_items = columns.get("english text__bullets", [])
        if bullet_items:
            blocks.append({"type": "bullets", "items": bullet_items})

        slide["content"]["blocks"] = blocks

        if slide["slide_type"] == "engage2":
            labels = []
            for txt in columns.get("button labels", []):
                labels.extend([p.strip() for p in txt.split("|") if p.strip()])
            if labels:
                slide["content"]["button_labels"] = labels

    for tbl in doc.tables:
        if len(tbl.rows) < 3:
            continue

        row_idx = 0
        slide = None
        columns: Dict[str, List[str]] = {}
        col_labels: List[str] = []

        while row_idx < len(tbl.rows):
            row = tbl.rows[row_idx]
            first_cell = normalize(row.cells[0].text)

            # -------------------------------
            # Start of slide
            # -------------------------------
            if (
                first_cell.lower().startswith("slide (header)")
                or first_cell.lower().startswith("header:")
            ):
                if slide:
                    finalize_slide(slide, columns)
                    module["slides"].append(slide)

                slide_index += 1
                slide = {
                    "id": f"slide_{slide_index:03d}",
                    "header": first_cell,
                    "slide_type": "panel",
                    "image": None,
                    "notes": "",
                    "content": {"blocks": []},
                }

                # reset Engage1 state for new slide
                engage1_mode = False
                engage1_intro_row_pending = False
                engage1_single_image_mode = False
                engage_intro_parts = []
                engage_intro_image = None
                engage_items = []
                engage_intro_notes = []

                label_row = tbl.rows[row_idx + 1]
                col_labels = [canonical_col_label(c.text) for c in label_row.cells]
                columns = {label: [] for label in col_labels if label}

                row_idx += 2
                continue

            # -------------------------------
            # Build row-wise texts per column (so Engage1 can be row-based)
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

            # Always preserve NOTES structurally (stage-level notes output)
            # This matches what your pipeline has already been doing.
            if notes_texts:
                columns.setdefault("notes and instructions", []).extend(notes_texts)

            # -------------------------------
            # Engage1 detection: INTRO ROW is the row whose NOTES contains "Slide Type = Engage 1"
            # (This is EXACTLY what your inspection output shows.)
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
                # Button labels block starts when Image cell == "Button Labels"
                if img_texts and img_texts[0].strip().lower() == "button labels":
                    collecting_button_labels = True

                    # IMPORTANT: the first label is on THIS SAME ROW in your docs
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
                        # Detect the "single image fixed location" Engage1 variant
                        blob_notes = " ".join(t.lower() for t in notes_texts)
                        if "single image in fixed location" in blob_notes:
                            engage1_single_image_mode = True
                    # after this row, intro is done; following rows are items
                    engage1_intro_row_pending = False
                    row_idx += 1
                    continue

                # Item rows: each row with an image is a new item
                if img_texts:
                    item = {
                        "button_label": None,
                        "image": " ".join(img_texts).strip(),
                        "body": list(eng_texts) if eng_texts else [],
                        "notes": "\n".join(notes_texts).strip() if notes_texts else None,
                    }
                    engage_items.append(item)
                    row_idx += 1
                    continue

                # ✅ NEW: "single image fixed location" variant
                # If the slide uses one fixed image, item rows may have NO image text.
                # In that case, each english-text row becomes an item.
                if engage1_single_image_mode and eng_texts:
                    item = {
                        "button_label": None,
                        "image": None,
                        "body": list(eng_texts),
                        "notes": "\n".join(notes_texts).strip() if notes_texts else None,
                    }
                    engage_items.append(item)
                    row_idx += 1
                    continue

                # If a row has no image but has english text, append to last item body
                if eng_texts and engage_items:
                    engage_items[-1]["body"].extend(eng_texts)

                # If a row has notes but no image, attach to last item notes
                if notes_texts and engage_items and not img_texts:
                    existing = engage_items[-1].get("notes")
                    extra = "\n".join(notes_texts).strip()
                    if extra:
                        engage_items[-1]["notes"] = (existing + "\n" + extra).strip() if existing else extra

                row_idx += 1
                continue

            # -------------------------------
            # DEFAULT (NON-ENGAGE1) parsing: keep your existing bullet logic intact
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

        if slide:
            finalize_slide(slide, columns)
            module["slides"].append(slide)

    return module


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Stage 1 v3 extractor (fixed bullets + no loss)"
    )

    parser.add_argument("--in", dest="in_path", required=False)
    parser.add_argument("--out", dest="out_path", required=False)

    args = parser.parse_args()

    # ----------------------------------------
    # AUTO-DETECT INPUT DOCX IF NOT PROVIDED
    # ----------------------------------------
    raw_dir = Path("data/raw")

    if not args.in_path:
        docx_files = list(raw_dir.glob("*.docx"))

        if len(docx_files) == 0:
            raise SystemExit("❌ No Word documents found in data/raw")

        if len(docx_files) > 1:
            raise SystemExit(
                f"❌ Multiple Word documents found in data/raw: {[f.name for f in docx_files]}"
            )

        input_path = docx_files[0]
    else:
        input_path = Path(args.in_path)

    # ----------------------------------------
    # DETERMINE OUTPUT PATH
    # ----------------------------------------
    if args.out_path:
        output_path = Path(args.out_path)
    else:
        output_path = Path("data/processed/module_v3.json")

    # run extraction
    module = extract_tables_v3(input_path)

    # write output
    output_path.write_text(
        json.dumps(module, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"✅ Using input: {input_path.name}")
    print(f"✅ Output written to: {output_path}")
    print(f"✅ Extracted {len(module['slides'])} slides")


if __name__ == "__main__":
    main()
