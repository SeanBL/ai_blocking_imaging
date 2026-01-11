from __future__ import annotations

from typing import List, Tuple

from docx.document import Document
from docx.shared import Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.shared import OxmlElement, qn
from docx.shared import RGBColor

BLUE = RGBColor(0x00, 0x70, 0xC0)
RED = RGBColor(0xC0, 0x00, 0x00)

# One row = (image_cell_text, english_text, notes_text)
RowTriple = Tuple[str, str, str]


def init_document_styles(doc: Document) -> None:
    # Keep it simple + deterministic (you can expand later)
    section = doc.sections[0]
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.6)
    section.right_margin = Inches(0.6)


def _set_cell_shading(cell, fill_hex: str) -> None:
    """
    Deterministic header shading without relying on Word themes.
    """
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tc_pr.append(shd)


def add_slide_table(doc: Document, header_text: str, rows: List[RowTriple]) -> None:
    """
    Creates one table per slide:
      Row 0: merged header
      Row 1: column labels
      Row 2+: content rows
    """
    # +2 for header + labels
    table = doc.add_table(rows=len(rows) + 2, cols=3)
    table.style = "Table Grid"

    # Column widths (tweak to match your authoring doc)
    col_widths = [Inches(1.4), Inches(4.6), Inches(2.0)]
    for col_idx, w in enumerate(col_widths):
        for r in table.rows:
            r.cells[col_idx].width = w

    # Row 0: merged header
    hdr = table.rows[0].cells
    merged = hdr[0].merge(hdr[1]).merge(hdr[2])
    p = merged.paragraphs[0]
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = p.add_run(header_text)
    run.bold = True
    run.font.color.rgb = BLUE
    _set_cell_shading(merged, "D9D9D9")

    # Row 1: labels
    labels = table.rows[1].cells
    labels[0].text = "Image"
    labels[1].text = "English Text"
    labels[2].text = "Notes and Instructions"
    for c in labels:
        _set_cell_shading(c, "EFEFEF")
        for run in c.paragraphs[0].runs:
            run.bold = True
            run.font.color.rgb = BLUE

    # Content rows
    for i, (img_txt, eng_txt, notes_txt) in enumerate(rows, start=2):
        cells = table.rows[i].cells
        cells[0].text = img_txt or ""
        cell = cells[1]
        cell.text = ""  # clear default paragraph

        if isinstance(eng_txt, list):
            for text, is_bullet in eng_txt:
                p = cell.add_paragraph()
                p.add_run(text)   # ← NO color set
                if is_bullet:
                    p.style = "List Bullet"
        else:
            cell.text = eng_txt or ""

        notes_cell = cells[2]
        notes_cell.text = ""

        if notes_txt:
            p = notes_cell.add_paragraph()

            if "Slide Type = Engage 1" in notes_txt:
                before, after = notes_txt.split("Slide Type = Engage 1", 1)

                if before.strip():
                    p.add_run(before)  # normal color

                r = p.add_run("Slide Type = Engage 1")
                r.font.color.rgb = RED
                r.bold = True

                if after.strip():
                    p.add_run(after)   # normal color
            else:
                p.add_run(notes_txt)   # normal color



