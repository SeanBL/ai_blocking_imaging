# `src/pipeline/`

## Purpose

This directory contains **pipeline orchestration scripts**.

These scripts **do not perform transformations** and **do not infer pedagogy**.  
Their sole responsibility is to **run existing stages in the correct order and enforce structural fidelity contracts**.

Think of this folder as the **gatekeeper layer** of the project.

---

## What this folder is **NOT**

- ❌ Not a stage
- ❌ Not a transformer
- ❌ Not an inference layer
- ❌ Not a place to add business logic

All extraction and transformation logic lives in `src/stage*`.

---

## `run_pre_llm_pipeline.py`

### What it does

`run_pre_llm_pipeline.py` runs the **structural, pre-LLM portion of the pipeline** with hard safety guarantees.

It executes **exactly** the following steps, in order:

1. **Stage 1**  
   Word (`.docx`) → Stage 1 JSON (`module_v3.json`)

2. **Stage 1.1 — Fidelity Audit (HARD GATE)**  
   Verifies that **all slide-owned text in the Word document** exists in Stage 1 output  
   - Uses raw Word XML as ground truth  
   - Fails immediately if *any* text is missing

3. **Stage 2**  
   Stage 1 JSON → Stage 2 JSON (`module_stage2.json`)

4. **Stage 2.1 — Preservation Audit (HARD GATE)**  
   Verifies that **Stage 2 preserved all text extracted by Stage 1**  
   - No creation  
   - No deletion  
   - No inference

If **any audit fails**, the pipeline stops immediately.

If both audits pass, the pipeline exits successfully and it is **safe to proceed to Stage 2.7+ (LLM-based stages)**.

---

### What it intentionally does **NOT** do

- ❌ Does NOT run Stage 2.7+
- ❌ Does NOT perform LLM inference
- ❌ Does NOT modify pedagogy or structure
- ❌ Does NOT replace individual stage CLIs

This is a **structural safety wrapper**, nothing more.

---

## Expected project structure

src/
stage1/
stage1_1/
stage2/
stage2_1/
stage2_7/
pipeline/
init.py
run_pre_llm_pipeline.py

data/
raw/
<single .docx file>
processed/
module_v3.json
module_stage2.json


---

## How input resolution works

- `run_pre_llm_pipeline.py` expects **exactly one** `.docx` file in `data/raw/`
- Outputs are written to `data/processed/`
- This mirrors the behavior of existing stage scripts for consistency

If multiple Word files are present, the pipeline fails fast.

---

## How to run

From the project root:

```bash
python -m src.pipeline.run_pre_llm_pipeline


This single command replaces the manual sequence:

python -m src.stage1.extract_tables_v3
python -m src.stage1_1.run_stage1_1
python -m src.stage2.transform_stage2
python -m src.stage2_1.run_stage2_1


…but with hard enforcement instead of trust.





python -m src.pipeline.run_pre_llm_pipeline