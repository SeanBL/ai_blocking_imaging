# src/stage3/validate_module.py

from __future__ import annotations
import json
import pathlib
import sys

from jsonschema import validate, Draft202012Validator
from jsonschema.exceptions import ValidationError

from .schema.module_schema import MODULE_SCHEMA


def load_json(path: pathlib.Path):
    """Load a JSON file with UTF-8 encoding."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load JSON file: {path}")
        raise e


def format_error(error: ValidationError) -> str:
    """
    Convert a jsonschema ValidationError into a readable string
    showing EXACTLY where the error occurred.
    """
    location = " → ".join(str(x) for x in error.path)
    schema_path = " → ".join(str(x) for x in error.schema_path)

    return (
        "❌ VALIDATION ERROR\n"
        f"- Message: {error.message}\n"
        f"- Data location: {location or '[root]'}\n"
        f"- Schema path: {schema_path}\n"
    )


def validate_module_json(module_json: dict) -> bool:
    """
    Validate module.json against the official schema.
    Returns True if valid; False otherwise.
    """
    validator = Draft202012Validator(MODULE_SCHEMA)

    errors = sorted(validator.iter_errors(module_json), key=lambda e: e.path)

    if not errors:
        print("✅ module.json is VALID")
        return True

    print(f"❌ Found {len(errors)} error(s):\n")
    for err in errors:
        print(format_error(err))

    return False


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("   python -m src.stage3.validate_module <module.json path>")
        print("\nExample:")
        print("   python -m src.stage3.validate_module data/final/huntington.json")
        return

    json_path = pathlib.Path(sys.argv[1])

    if not json_path.exists():
        print(f"❌ File not found: {json_path}")
        return

    print(f"Validating: {json_path}\n")

    data = load_json(json_path)
    validate_module_json(data)


if __name__ == "__main__":
    main()
