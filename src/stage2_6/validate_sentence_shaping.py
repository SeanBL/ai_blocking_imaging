from typing import Dict, Any, List
import re

WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)

def _word_count(text: str) -> int:
    return len(WORD_RE.findall(text or ""))

def validate_sentence_shaping(
    raw: Dict[str, Any],
    source_text: str,
) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Sentence shaping output must be a JSON object.")

    shaping = raw.get("sentence_shaping")
    if not isinstance(shaping, dict):
        raise ValueError("Missing 'sentence_shaping' object.")

    groups = shaping.get("groups")

    normalized_source = " ".join((source_text or "").split())

    # ✅ NO-OP CASE
    if not isinstance(groups, list) or len(groups) == 0:
        sentences = [
            s.strip()
            for s in re.split(r'(?<=[.!?])\s+', normalized_source)
            if s.strip()
        ]
        return {
            "sentence_blocks": [
                {
                    "sentences": sentences,
                    "word_count": _word_count(normalized_source),
                }
            ]
        }

    used_text_parts: List[str] = []
    sentence_blocks: List[Dict[str, Any]] = []

    for i, group in enumerate(groups, start=1):
        sentences = group.get("sentences")
        if not isinstance(sentences, list):
            raise ValueError(f"Group {i} missing sentences list.")

        if not (1 <= len(sentences) <= 2):
            raise ValueError(f"Group {i} has {len(sentences)} sentences (must be 1–2).")

        cleaned: List[str] = []
        for s in sentences:
            if not isinstance(s, str) or not s.strip():
                raise ValueError(f"Invalid sentence in group {i}.")
            s_clean = " ".join(s.split())
            if s_clean not in normalized_source:
                raise ValueError(f"Sentence not found verbatim in source text:\n{s}")
            cleaned.append(s_clean)
            used_text_parts.append(s_clean)

        wc = _word_count(" ".join(cleaned))
        if wc < 5:
            raise ValueError(f"Group {i} is implausibly short ({wc} words).")

        sentence_blocks.append(
            {
                "sentences": cleaned,
                "word_count": wc,
            }
        )

    normalized_used = " ".join(" ".join(used_text_parts).split())

    if normalized_used != normalized_source:
        raise ValueError("Shaped sentences do not reconstruct source text exactly.")

    return {"sentence_blocks": sentence_blocks}
