import pytest

from src.stage2_8.run_stage2_8 import run_stage2_8
from src.stage2_8.quiz_slide_builder import (
    build_inline_quiz_slide,
    build_final_quiz_slide,
)
from src.stage2_8.quiz_insert import insert_quiz_slides


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def panel_slide(text, notes=None):
    return {
        "slide_type": "panel",
        "notes": notes,
        "content": {
            "blocks": [{"type": "paragraph", "text": text}]
        },
    }


def mock_quiz_payload(quiz_id, total_questions):
    return {
        "quiz_id": quiz_id,
        "questions": [
            {
                "question_id": f"q{i+1}",
                "type": "mcq",
                "prompt": f"Question {i+1}",
                "options": {
                    "A": "A",
                    "B": "B",
                    "C": "C",
                    "D": "D",
                },
                "correct_answer": "A",
                "rationale": "Because."
            }
            for i in range(total_questions)
        ],
    }


# -------------------------------------------------
# Monkeypatch run_quiz_pipeline
# -------------------------------------------------

@pytest.fixture
def mock_runner(monkeypatch):
    def _mock_run_quiz_pipeline(*, quiz_id, total_questions, **kwargs):
        return mock_quiz_payload(quiz_id, total_questions)

    monkeypatch.setattr(
        "src.stage2_8.run_stage2_8.run_quiz_pipeline",
        _mock_run_quiz_pipeline,
    )


# -------------------------------------------------
# Integration Tests
# -------------------------------------------------

def test_single_quiz_inline_and_final(mock_runner):
    module = {
        "slides": [
            panel_slide("Intro", notes="[[QUIZ:1]]"),
            panel_slide("Concept A"),
            panel_slide("Concept B"),
            panel_slide("End", notes="[[QUIZ:1:QUESTIONS=2,1]]"),
        ]
    }

    result = run_stage2_8(
        client=None,
        model="mock",
        module_json=module,
    )

    assert 1 in result["inline_quizzes"]
    assert 1 in result["final_quizzes"]

    inline = result["inline_quizzes"][1]
    final = result["final_quizzes"][1]

    assert len(inline["questions"]) == 2
    assert len(final["questions"]) == 1

    inline_slide = build_inline_quiz_slide(
        quiz_id=1,
        questions=inline["questions"],
    )

    final_slide = build_final_quiz_slide(
        quiz_id=1,
        questions=final["questions"],
    )

    new_slides = insert_quiz_slides(
        slides=module["slides"],
        inline_quizzes={
            1: {
                "insert_after_index": inline["insert_after_index"],
                "slide": inline_slide,
            }
        },
        final_quizzes={1: final_slide},
    )

    # Inline quiz appears immediately after insertion marker
    assert new_slides[4]["id"] == "quiz_1_inline"

    # Final quiz is last
    assert new_slides[-1]["id"] == "quiz_1_final"


def test_inline_only_quiz(mock_runner):
    module = {
        "slides": [
            panel_slide("Intro", notes="[[QUIZ:2]]"),
            panel_slide("Concept A"),
            panel_slide("End", notes="[[QUIZ:2:QUESTIONS=2,0]]"),
        ]
    }

    result = run_stage2_8(
        client=None,
        model="mock",
        module_json=module,
    )

    assert 2 in result["inline_quizzes"]
    assert 2 not in result["final_quizzes"]


def test_final_only_quiz(mock_runner):
    module = {
        "slides": [
            panel_slide("Intro", notes="[[QUIZ:3]]"),
            panel_slide("Concept A"),
            panel_slide("End", notes="[[QUIZ:3:QUESTIONS=0,2]]"),
        ]
    }

    result = run_stage2_8(
        client=None,
        model="mock",
        module_json=module,
    )

    assert 3 not in result["inline_quizzes"]
    assert 3 in result["final_quizzes"]


def test_missing_panel_content_fails(mock_runner):
    module = {
        "slides": [
            {
                "slide_type": "engage",
                "notes": "[[QUIZ:4]]",
                "content": {},
            },
            {
                "slide_type": "engage",
                "notes": "[[QUIZ:4:QUESTIONS=1,0]]",
                "content": {},
            },
        ]
    }

    with pytest.raises(ValueError):
        run_stage2_8(
            client=None,
            model="mock",
            module_json=module,
        )
