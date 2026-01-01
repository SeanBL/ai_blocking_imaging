# src/stage2_8/logger.py
import logging

logger = logging.getLogger("stage2_8")

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[Stage 2.8] %(levelname)s — %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
