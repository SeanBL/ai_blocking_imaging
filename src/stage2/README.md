# Stage 2 — Deterministic Normalization (NO LLM)

## Purpose (plain English)
Stage 1 correctly reads complex Word tables and produces JSON.
However, Stage 1 output can still have small structural variations:
- strings vs lists of paragraphs
- engage item keys named differently
- missing engage intro wrappers
- engage2 build stored under different keys

Stage 2 fixes ONLY the *shape*, not the meaning.

Stage 2 does NOT:
- parse Word
- rewrite text
- split/merge paragraphs
- call any LLM/API

Stage 2 DOES:
- Normalize Engage 1 into:
  - intro { title, content[] }
  - items[] { button_label, title, content[] }
- Normalize Engage 2 into:
  - button_label (single progressive button)
  - build[] { title, content[] }
- Preserve panels/pages as-is (only whitespace + list normalization)

## Inputs / Outputs
Input:  module_v3.json  (Stage 1 output)
Output: module_stage2.json (canonical, renderer-friendly)

## Run
python -m src.stage2.stage2_transform \
  data/processed/module_v3.json \
  data/processed/module_stage2.json


---

## Stage 2 Renderer (Final Assembly)

Stage 2.5 and Stage 2.6 do **not** modify the module directly.
They produce *suggestions* only.

The Stage 2 renderer is responsible for:
- Applying panel splits from Stage 2.5 (`panel_final`)
- Applying sentence shaping from Stage 2.6
- Producing the final, renderer-ready Stage 2 module

The renderer is:
- Deterministic
- LLM-free
- Order-preserving
- Guaranteed not to modify wording

### Renderer Input / Output

Inputs:
- `module_stage2.json` (base normalized module)
- `module_stage2_5_suggestions.json`
- `module_stage2_6_suggestions.json`

Output:
- `module_stage2_final.json`

### Run Renderer

```bash
python -m src.stage2.render_module \
  data/processed/module_stage2.json \
  data/processed/module_stage2_5_suggestions.json \
  data/processed/module_stage2_6_suggestions.json \
  data/processed/module_stage2_final.json