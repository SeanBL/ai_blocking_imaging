from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List


def collect_final_exam(
    *,
    stage2_quiz_dir: Path,
    output_path: Path
) -> Dict[str, Any]:
    """
    Collects all quiz questions marked reserve_for_final_exam = true
    and outputs them into a single final_exam.json file.

    Inputs:
      - stage2_quiz_dir: directory of per-header quiz JSON files
      - output_path: path to write final_exam.json
    """

    exam_questions: List[Dict[str, Any]] = []

    for file_path in sorted(stage2_quiz_dir.glob("*.json")):
        with open(file_path, "r", encoding="utf-8") as f:
            block = json.load(f)

        header = block.get("header", "")
        quiz = block.get("quiz", [])

        if not isinstance(quiz, list):
            continue

        for q in quiz:
            if q.get("reserve_for_final_exam") is True:
                exam_questions.append({
                    "source_header": header,
                    "question": q.get("question"),
                    "options": q.get("options", []),
                    "correct_answers": q.get("correct_answers", []),
                    "type": q.get("type"),
                })

    final_exam = {
        "final_exam": exam_questions
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_exam, f, indent=2, ensure_ascii=False)

    return final_exam
