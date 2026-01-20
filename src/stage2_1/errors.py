from __future__ import annotations

from typing import List


class FidelityAuditError(RuntimeError):
    """
    Raised when Stage 2.1 detects that text present in the Word document
    is missing from Stage 2 output.

    This is a HARD FAILURE.
    """

    def __init__(self, *, missing_fragments: List[str]):
        self.missing_fragments = missing_fragments

        preview = "\n".join(f"- {frag}" for frag in missing_fragments[:5])
        message = (
            f"Stage 2.1 Fidelity Audit FAILED — "
            f"{len(missing_fragments)} text fragment(s) missing.\n"
            f"First missing fragments:\n{preview}"
        )

        super().__init__(message)
