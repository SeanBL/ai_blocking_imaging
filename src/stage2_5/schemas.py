# src/stage2_5/schemas.py

PANEL_LENGTH_ANALYSIS_ACTIONS = {"none", "reflow", "split"}
SENTENCE_REFLOW_ACTIONS = {"none", "reflow"}
ENGAGE_CONFIDENCE = {"low", "medium", "high"}
ENGAGE_ITEM_STATUS = {"ok", "exceeds_soft_limit", "exceeds_hard_limit"}
BUTTON_TARGETS = {"engage1_item", "engage2"}

REQUIRED_SAFETY_KEYS = {"adds_new_information", "removes_information", "medical_facts_changed"}
