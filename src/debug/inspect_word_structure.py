from docx import Document
from docx.oxml.ns import qn
from pathlib import Path
import sys


def inspect_docx(path: Path) -> None:
    doc = Document(path)

    print(f"\nInspecting: {path}\n")

    for ti, table in enumerate(doc.tables):
        print(f"\n=== TABLE {ti} ===")

        for ri, row in enumerate(table.rows):
            print(f"\n-- Row {ri} --")

            for ci, cell in enumerate(row.cells):
                print(f"\nCell {ci}:")

                for pi, p in enumerate(cell.paragraphs):
                    text = p.text.strip()
                    style = p.style.name if p.style else "None"

                    # Check numbering (bullets / lists)
                    numPr = p._p.find(qn("w:numPr"))
                    has_numbering = numPr is not None

                    print(
                        f"  P{pi}: "
                        f"text='{text}' | "
                        f"style='{style}' | "
                        f"numbered={has_numbering}"
                    )


def main(argv):
    if len(argv) != 2:
        print(
            "Usage:\n"
            "  python -m src.debug.inspect_word_structure <docx_path>"
        )
        return 1

    inspect_docx(Path(argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
