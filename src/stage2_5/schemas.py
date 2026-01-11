# src/stage2_5/schemas.py

# Stage 2.5 outputs only these panel actions
PANEL_FINAL_ACTIONS = {"keep", "split"}

ENGAGE_ITEM_STATUS = {
    "ok",
    "exceeds_soft_limit",
    "exceeds_hard_limit",
}

BUTTON_TARGETS = {"engage1_item", "engage2"}

REQUIRED_SAFETY_KEYS = {
    "adds_new_information",
    "removes_information",
    "medical_facts_changed",
}