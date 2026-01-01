import copy

from stage2.stage2_transform import normalize_engage2_structure


def test_engage2_preserved_when_already_structured():
    """
    Regression test:
    If an Engage 2 slide already has intro + steps,
    normalize_engage2_structure MUST preserve it exactly.
    """

    slide = {
        "id": "slide_999",
        "slide_type": "engage2",
        "header": "Test Engage 2",
        "notes": "Slide Type = Engage 2",
        "uuid": "stage2-999",
        "type": "engage2",
        "intro": {
            "title": "",
            "content": ["Intro paragraph"]
        },
        "button": {
            "label": "Next"
        },
        "steps": [
            {"content": ["Step one text"]},
            {"content": ["Step two text"]},
        ],
    }

    original = copy.deepcopy(slide)

    result = normalize_engage2_structure(slide, index=999)

    # Structure preserved
    assert result["type"] == "engage2"
    assert result["intro"] == original["intro"]
    assert result["button"] == original["button"]
    assert result["steps"] == original["steps"]

    # No flattening or content recreation
    assert "content" not in result
