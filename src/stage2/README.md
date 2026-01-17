## Stage 2 — Deterministic Normalization

### Purpose

Stage 2 converts the structurally faithful output of Stage 1 into a **canonical, deterministic JSON schema**.

Stage 2 performs **no pedagogy inference**, **no content creation**, and **no interpretation**.  
Its only responsibility is to normalize structure, whitespace, and field placement so downstream stages can rely on a stable shape.

---

### Inputs

Stage 2 consumes the JSON produced by Stage 1 and assumes:

- Slide boundaries are already correct
- `slide_type` is authoritative (`panel`, `engage1`, `engage2`)
- All text has already been extracted from the Word document
- Button labels (if any) already exist
- No semantic interpretation is required

Stage 2 trusts Stage 1 and does not attempt to repair or reinterpret it.

---

### Outputs

Stage 2 emits a normalized module JSON with:

- Deterministic UUIDs (preserved if present, generated if missing)
- Normalized whitespace (trimmed, collapsed, NBSP removed)
- Canonical slide schemas based on `slide_type`
- Preserved content ordering

No information is added, removed, or inferred.

---

### Slide Normalization

#### Panel Slides

- `header`, `image`, and `notes` are preserved
- `content.blocks` is preserved exactly
- Paragraphs and bullet lists remain unchanged

No restructuring or interpretation occurs.

---

#### Engage 1 Slides

- Intro content is preserved
- Engage items are preserved
- Per-item images and button labels are preserved
- No items or labels are created or modified

Stage 2 does not assign pedagogical meaning.

---

#### Engage 2 Slides

- `content.button_labels` from Stage 1 are preserved verbatim
- Paragraph blocks are reshaped into a sequential `build` list
- Ordering is preserved exactly
- No button labels are inferred or synthesized

Stage 2 does not infer build logic or invent defaults.

---

### Explicit Non-Responsibilities

Stage 2 must never:

- Create or infer button labels
- Invent default values (e.g. "Next")
- Interpret pedagogical intent
- Decide build sequencing logic
- Create or remove slides
- Reorder content
- Modify semantic meaning

## Run
python -m src.stage2.stage2_transform \
  data/processed/module_v3.json \
  data/processed/module_stage2.json


