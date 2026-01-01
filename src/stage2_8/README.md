# Stage 2.8 — Quiz Generation & Insertion

Stage 2.8 generates professional, undergraduate-level quiz questions
from authored module content and inserts quiz slides into the final
canonical module JSON.

This stage is **fully deterministic**, **LLM-audited**, and **fails fast**.

---

## Where Stage 2.8 Fits in the Pipeline

The correct order is:

Stage 2.7 → Stage 2.5 → Stage 2.6 → **Stage 2.8**

Why:

- Stage 2.7 preserves **notes**, which contain quiz markers
- Stage 2.5 produces **panel split decisions only**
- Stage 2.6 applies **sentence shaping overlays**
- Stage 2.8 inserts **new quiz slides**

Stage 2.8 must run **after Stage 2.6** so that quiz slides are not
modified or reshaped by later stages.

---

## Will Stage 2.8 Break Stage 2.5 or Stage 2.6?

**No. By design.**

- Stage 2.5 runs earlier and is unaffected.
- Stage 2.6 only modifies `slide_type == "panel"`.
- Quiz slides use `slide_type == "quiz"` and must be passed through unchanged.

Quiz slides are treated the same as Engage slides: **immutable**.

---

## Quiz Markers

Quiz markers appear in slide `notes`:

python -m src.stage2_8.stage2_8_main