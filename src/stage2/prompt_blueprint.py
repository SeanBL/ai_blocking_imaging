def build_user_prompt(block):
    """
    Build the USER section of the LLM prompt.
    The SYSTEM section is loaded from config/prompt_blueprint.txt.
    """

    paragraphs = "\n".join(block.english_text_raw)
    header = block.header
    notes = block.notes_raw or ""

    return f"""
HEADER: {header}

RAW PARAGRAPHS (DO NOT CHANGE MEANING):
{paragraphs}

NOTES:
{notes}

TASK:
- Apply Option B light rewrite rules as described in the system prompt.
- Preserve all medical meaning.
- Determine whether each paragraph becomes:
    * a page
    * an engage
    * or an engage2
- Split long paragraphs by natural sentence boundaries.
- NO image selection in this stage.
- NO quiz generation.
- Output JSON only.
"""

