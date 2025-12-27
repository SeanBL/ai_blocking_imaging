# Stage 1 — Word → Raw Module JSON Extraction (LOCKED)

## Purpose (Plain English)

Stage 1 reads a medically authored Microsoft Word (`.docx`) file and converts it into a
**faithful raw JSON representation** of the learning module.

Its ONLY responsibility is to **extract structure and content accurately** from Word tables.

Stage 1 does NOT interpret meaning, normalize schemas, or prepare content for rendering.

Once Stage 1 is correct, it must remain **locked and unchanged**, because all later stages
depend on its output.

---

## What Stage 1 Does

Stage 1:

- Parses complex Word tables
- Preserves author intent and paragraph order
- Extracts content exactly as written
- Outputs a raw but structurally accurate `module_v3.json`
- Handles real-world Word formatting quirks

Specifically, Stage 1 correctly handles:

- Multiple slides per table
- Panel vs Engage vs Engage2 detection
- Engage button labels
- Engage2 progressive structures
- Notes vs visible learner content
- Repeated header rows
- Empty cells and merged cells
- Paragraph order preservation

Stage 1 is intentionally **forgiving of Word authoring inconsistencies**.

---

## What Stage 1 Does NOT Do

Stage 1 does NOT:

- Normalize JSON shapes
- Guarantee consistent schemas
- Rewrite, summarize, or simplify text
- Split or merge paragraphs
- Decide rendering behavior
- Select images
- Create quizzes
- Call an LLM or external API
- Infer pedagogy or instructional intent

All of the above belong to later stages.

---

## Input / Output

### Input

- A medically authored `.docx` file
- Uses tables as the primary structure
- May contain merged cells, repeated headers, empty rows, or notes

### Output

- `module_v3.json`
- This output is **raw but correct**
- Some fields may vary in shape (e.g., string vs list, optional keys present/missing)

Example (simplified):

```json
{
  "module_title": "Huntington’s Disease",
  "slides": [
    {
      "type": "panel",
      "header": "Introduction",
      "content": [
        "Huntington’s disease is an inherited progressive brain disease..."
      ],
      "notes": null
    },
    {
      "type": "engage",
      "header": "Key Symptoms",
      "intro": "Let’s explore common symptoms.",
      "items": [
        {
          "button_label": "Movement",
          "content": "Chorea involves involuntary movements..."
        }
      ]
    }
  ]
}

python src/stage1/stage1_extract_v3.py \
  --in data/raw/1561_Advanced_Training_Child_Health.docx \
  --out data/processed/module_v3.json
