from src.stage2_6.validate_sentence_shaping import validate_sentence_shaping

def test_two_sentence_panel_splits_into_two_blocks():
    panel_text = (
        "Children in Low Middle-Income Countries (LMIC) face multiple threats from infectious diseases. "
        "In addition, diagnostic and treatment services are limited in these settings."
    )

    llm_output = {
        "sentence_shaping": {
            "action": "shape",
            "groups": [
                {
                    "sentences": [
                        "Children in Low Middle-Income Countries (LMIC) face multiple threats from infectious diseases."
                    ],
                    "word_count": 12
                },
                {
                    "sentences": [
                        "In addition, diagnostic and treatment services are limited in these settings."
                    ],
                    "word_count": 11
                }
            ]
        },
        "safety": {
            "wording_changed": False,
            "content_removed": False,
            "content_added": False
        }
    }

    result = validate_sentence_shaping(llm_output, panel_text)

    assert len(result["groups"]) == 2
