import logging

logger = logging.getLogger("stage2_review")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter("[Stage 2 Review] %(levelname)s — %(message)s")
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)
