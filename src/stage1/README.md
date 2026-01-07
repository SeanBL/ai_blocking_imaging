# Stage 1 — Word → Raw Module JSON Extraction (**LOCKED**)

## Purpose (Plain English)

Stage 1 reads a medically authored Microsoft Word (`.docx`) file and converts it into a  
**faithful, lossless JSON representation** of the module’s structure and content.

Its **only responsibility** is to extract what exists in the Word document **exactly as authored**.

Stage 1 **does not interpret meaning, infer pedagogy, or prepare content for rendering**.

Once Stage 1 is correct, it must remain **locked and unchanged**, because every downstream
stage depends on its output being stable and trustworthy.

---

## Stage 1 Invariant Contract (DO NOT VIOLATE)

Stage 1 is a **STRUCTURAL extractor only**.

**Invariants:**

1. Paragraphs in Word are preserved as paragraphs in JSON.
2. Bulleted / numbered lists explicitly marked by Word are preserved as bullets.
3. Mixed prose + bullets in the same cell are preserved **in order**.
4. Stage 1 **NEVER infers** pedagogy, engages, quizzes, or instructional intent.

If any invariant is broken, downstream stages become unreliable.

---

## What Stage 1 Does

Stage 1:

- Parses complex Word tables into slides
- Preserves paragraph order and grouping
- Extracts content **exactly as written**
- Preserves notes verbatim
- Outputs a raw but structurally accurate `module_v3.json`
- Tolerates real-world Word authoring inconsistencies

Specifically, Stage 1 correctly handles:

- Multiple slides per table
- Repeated header rows
- Empty cells and merged cells
- Paragraph vs bullet detection
- Mixed prose + bullets in the same cell
- Notes vs learner-visible content
- Engage 1 and Engage 2 **when already structurally authored**
- Button label rows (when present)
- Progressive Engage2 layouts

Stage 1 is intentionally **forgiving of Word formatting quirks**  
and **never fails due to authoring style alone**.

---

## What Stage 1 Does NOT Do

Stage 1 does **NOT**:

- Normalize JSON schemas
- Enforce consistent field shapes
- Rewrite, summarize, or split text
- Apply word-count limits
- Decide rendering behavior
- Select or validate images
- Create quizzes
- Call an LLM or external API
- Infer whether something *should* be an engage

All interpretation, transformation, and pedagogy belong to **Stage 2 and beyond**.

---

## Structural vs Instructional Signals (CRITICAL)

Stage 1 **records signals** found in the Word document  
but **does not act on their meaning beyond structural parsing**.

There are **two categories of signals**:

### 1️⃣ Structural Signals (What the slide *already is*)

These affect how Stage 1 parses structure.

Examples (in *Notes and Instructions*):

Slide Type = Panel
Slide Type = Engage 1
Slide Type = Engage 2

yaml
Copy code

- These indicate the slide is **already authored** in that structure
- Stage 1 will parse Engage rows **only if the structure exists**
- Stage 1 does **not** validate correctness or completeness

---

### 2️⃣ Instructional Signals (What later stages may do)

These signals are **preserved verbatim** but ignored by Stage 1 logic.

Examples:

[[LOCKED]]
[[CREATE:ENGAGE1]]
[[CREATE:ENGAGE2]]

markdown
Copy code

- Stage 1 does not branch logic on these
- Stage 1 does not infer structure from them
- Stage 1 simply stores them in `notes`

Their meaning is interpreted **only in Stage 2+**.

---

## Interpretation Summary (Authoring Contract)

| Signal                      | Meaning                               | Stage 1 Behavior | Stage 2 Behavior        |
|----------------------------|----------------------------------------|------------------|-------------------------|
| `Slide Type = Engage 1`     | Already structured engage              | Parse structure  | Respect / validate      |
| `[[LOCKED]]`                | Do not modify                          | Preserve only    | Do not transform        |
| `[[CREATE:ENGAGE1]]`        | Engage needs to be created             | Preserve text    | Transform into engage   |
| *(none)*                    | Plain panel                            | Preserve         | Apply default rules     |

## Signal Combination Semantics

The following table defines how **combined signals** in the *Notes and Instructions* field
are interpreted across the pipeline.

| Combination                                 | Meaning                                |
| ------------------------------------------- | -------------------------------------- |
| `Slide Type = Engage 1` + `[[LOCKED]]`      | Author-authored engage, do not touch   |
| `Slide Type = Engage 1` (no locked)         | Engage, but Stage 2 may still validate |
| `Slide Type = Panel` + `[[CREATE:ENGAGE1]]` | LLM must create engage                 |
| `Slide Type = Panel` + no signals           | Normal panel rules apply               |


**Key principle:**  
> Stage 1 never guesses intent.  
> Stage 2 decides what to do with intent.

---

## Important Clarification About Engages

- Stage 1 **does NOT assume** that `Slide Type = Engage 1` means content is well-formed
- Stage 1 **does NOT attempt** to “fix” or “complete” engages
- If a slide contains paragraph text only, Stage 1 preserves it as paragraphs
- Even if `[[CREATE:ENGAGE1]]` is present, Stage 1 does nothing special

This ensures that:

- Poorly formatted engages are preserved for the LLM to transform
- Well-authored engages are preserved exactly
- No content is lost or prematurely restructured

---

## Quiz Creation Signals (Recorded in Stage 1, Interpreted in Stage 2)

Stage 1 **records quiz signals verbatim** but **does not act on them**.

---

### Quiz Signal Syntax

```text
[[QUIZ:n]]
[[QUIZ:n:QUESTIONS=a,b]]


Where:

n = quiz identifier

a,b = question counts (Stage 2 semantics)

Quiz Signal Semantics (Stage 2 Interpretation)

[[QUIZ:n]]
→ Marks the START of quiz source material

[[QUIZ:n:QUESTIONS=a,b]]
→ Marks the END of quiz source material
→ Instructs how many questions to generate

Quiz scope includes:

All slides from and including the slide containing [[QUIZ:n]]
up to and including the slide containing [[QUIZ:n:QUESTIONS=a,b]]

Stage Responsibilities for Quiz Signals
Signal Example	Meaning	Stage 1	Stage 2
[[QUIZ:1]]	Start quiz source	Store	Collect
[[QUIZ:1:QUESTIONS=3,3]]	End quiz + generation rules	Store	Generate
Missing terminator	Incomplete quiz range	Store	Error

## Input / Output

### Input

- A medically authored `.docx` file
- Uses Word tables as the primary structure
- May contain:
  - merged cells
  - repeated headers
  - empty rows
  - notes and metadata
  - inconsistent formatting

### Output

- `module_v3.json`
- Output is **raw but correct**
- Field shapes may vary (strings, lists, optional keys)
- No schema guarantees are enforced at this stage

---

## Final Rule

> **Stage 1 must be boring, faithful, and predictable.**  
> Any intelligence added here will break the pipeline.

This stage is **LOCKED** by design.

python src/stage1/stage1_extract_v3.py

