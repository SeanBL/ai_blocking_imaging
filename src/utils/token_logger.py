from __future__ import annotations
import json
import pathlib
import datetime
from typing import Optional

from .config_loader import load_settings

_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _get_logs_dir() -> pathlib.Path:
    settings = load_settings()
    logs_rel = settings.get("paths", {}).get("logs", "logs")
    logs_dir = _ROOT / logs_rel
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def log_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    provider: str = "openai",
) -> None:
    """
    Append a single usage record to logs/token_usage.jsonl with
    estimated cost using pricing from settings.yaml.
    """
    settings = load_settings()
    pricing = settings.get("pricing", {}).get(model, {})
    in_price = float(pricing.get("input_per_1k", 0.0))
    out_price = float(pricing.get("output_per_1k", 0.0))

    total_tokens = prompt_tokens + completion_tokens
    input_cost = (prompt_tokens / 1000.0) * in_price
    output_cost = (completion_tokens / 1000.0) * out_price
    total_cost = input_cost + output_cost

    record = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "provider": provider,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(total_cost, 6),
    }

    logs_dir = _get_logs_dir()
    usage_file = logs_dir / "token_usage.jsonl"
    with open(usage_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")