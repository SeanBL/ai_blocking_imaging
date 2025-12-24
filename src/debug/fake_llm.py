def fake_llm(prompt: str):
    print("\n--- LLM PROMPT START ---")
    print(prompt[:400])  # preview
    print("--- LLM PROMPT END ---\n")

    # Return a deliberately VALID structure
    return {
        "panel_length_analysis": {
            "word_count": 120,
            "sentence_count": 5,
            "action": "split",
            "reason": "Panel exceeds recommended length",
            "suggested_panels": [
                {
                    "sentences": [
                        "This is the first sentence of the first panel.",
                        "This is the second sentence of the first panel."
                    ]
                },
                {
                    "sentences": [
                        "This is the first sentence of the second panel.",
                        "This is the second sentence of the second panel."
                    ]
                }
            ]
        },
        "safety": {
            "adds_new_information": False,
            "removes_information": False,
            "medical_facts_changed": False
        }
    }
