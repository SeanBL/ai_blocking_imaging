import pytest

from src.stage2_8.quiz_detect import detect_quizzes
from src.stage2_8.quiz_extract import extract_quiz_source


def slide(notes=None, slide_type="panel", text="Example text"):
    return {
        "notes": notes,
        "slide_type": slide_type,
        "content": {
            "blocks": [{"type": "paragraph", "text": text}]
        }
    }


def test_start_without_insert_fails():
    slides = [
        slide(notes="[[QUIZ:1]]"),
        slide(),
    ]
    with pytest.raises(ValueError):
        detect_quizzes(slides)


def test_insert_without_start_fails():
    slides = [
        slide(notes="[[QUIZ:1:QUESTIONS=2,2]]"),
    ]
    with pytest.raises(ValueError):
        detect_quizzes(slides)


def test_zero_zero_questions_fails():
    slides = [
        slide(notes="[[QUIZ:1]]"),
        slide(notes="[[QUIZ:1:QUESTIONS=0,0]]"),
    ]
    with pytest.raises(ValueError):
        detect_quizzes(slides)


def test_no_panel_content_fails():
    slides = [
        slide(notes="[[QUIZ:1]]", slide_type="engage"),
        slide(notes="[[QUIZ:1:QUESTIONS=1,1]]", slide_type="engage"),
    ]
    quizzes = detect_quizzes(slides)
    with pytest.raises(ValueError):
        extract_quiz_source(slides, quizzes[1])


def test_valid_quiz_extracts_text():
    slides = [
        slide(notes="[[QUIZ:1]]", text="First concept"),
        slide(text="Second concept"),
        slide(notes="[[QUIZ:1:QUESTIONS=1,0]]"),
    ]
    quizzes = detect_quizzes(slides)
    source = extract_quiz_source(slides, quizzes[1])

    assert source == ["Second concept"]
