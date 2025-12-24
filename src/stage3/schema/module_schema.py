# src/stage3/schema/module_schema.py

MODULE_SCHEMA = {
    "type": "object",
    "required": ["module_title", "blocks"],
    "properties": {
        "module_title": {"type": "string"},
        "blocks": {
            "type": "array",
            "items": {"$ref": "#/definitions/block"}
        }
    },

    "definitions": {
        # ---------------------------------------------------------
        # BLOCK STRUCTURE
        # ---------------------------------------------------------
        "block": {
            "type": "object",
            "required": ["header", "pages", "quiz"],
            "properties": {
                "header": {"type": "string"},
                "notes": {"type": ["string", "null"]},
                "pages": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/page"}
                },
                "quiz": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/quiz_question"}
                }
            }
        },

        # ---------------------------------------------------------
        # PAGE (three possible shapes)
        # ---------------------------------------------------------
        "page": {
            "type": "object",
            "required": ["type"],
            "properties": {
                "uuid": {"type": "string"},
                "page_index": {"type": "integer"},
                "paragraph_index": {"type": ["integer", "null"]},

                "type": {
                    "type": "string",
                    "enum": ["page", "engage", "engage2"]
                },

                # Shared fields for all
                "title": {"type": "string"},
                "content": {"type": "string"},
                "image_id": {"type": ["string", "null"]},

                # bullets
                "bullet_points": {
                    "type": "array",
                    "items": {"type": "string"}
                },

                "button_label": {
                    "type": ["string", "null"]
                },

                # ENGAGE2 (single button, multiple steps)
                "step_points": {
                    "type": "array",
                    "items": {"type": "string"}
                },
            },

            # Conditional validation
            "oneOf": [
                {
                    # Normal page
                    "properties": {"type": {"const": "page"}}
                },
                {
                    # Engage
                    "properties": {"type": {"const": "engage"}}
                },
                {
                    # Engage2
                    "properties": {"type": {"const": "engage2"}}
                }
            ]
        },

        # ---------------------------------------------------------
        # QUIZ QUESTION
        # ---------------------------------------------------------
        "quiz_question": {
            "type": "object",
            "required": [
                "question",
                "options",
                "correct_answers",
                "type",
                "reserve_for_final_exam"
            ],
            "properties": {
                "question": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["single", "multiple", "true_false"]
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1
                },
                "correct_answers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1
                },
                "reserve_for_final_exam": {"type": "boolean"}
            }
        }
    }
}
