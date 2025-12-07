from __future__ import annotations
import pathlib
import yaml

# Root = project root (where src/ and data/ live)
_ROOT = pathlib.Path(__file__).resolve().parents[1]


def get_config_dir() -> pathlib.Path:
    return _ROOT / "config"


def load_settings() -> dict:
    """Load YAML settings once per process."""
    settings_path = get_config_dir() / "settings.yaml"
    with open(settings_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prompt(filename: str) -> str:
    """
    Load a prompt text file from src/config/.

    Example:
        load_prompt("prompt_blueprint.txt")
        load_prompt("prompt_quiz.txt")
    """
    prompt_path = get_config_dir() / filename
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()