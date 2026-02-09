from __future__ import annotations

import json
from pathlib import Path
from typing import Any


try:
    from jsonschema import Draft202012Validator, RefResolver
except ImportError:  # pragma: no cover
    Draft202012Validator = None
    RefResolver = None


class SchemaValidationError(ValueError):
    pass


def _load_schema(schema_path: Path) -> dict:
    with open(schema_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_dataset(data: Any, schema_dir: Path) -> None:
    _validate(data, schema_dir / "dataset.schema.json", schema_dir)


def validate_analysis_report(data: Any, schema_dir: Path) -> None:
    _validate(data, schema_dir / "analysis_report.schema.json", schema_dir)


def _validate(data: Any, schema_path: Path, schema_dir: Path) -> None:
    if Draft202012Validator is None or RefResolver is None:
        raise SchemaValidationError("jsonschema is required for schema validation.")

    schema = _load_schema(schema_path)
    resolver = RefResolver(base_uri=schema_dir.resolve().as_uri() + "/", referrer=schema)
    validator = Draft202012Validator(schema, resolver=resolver)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        messages = "; ".join(error.message for error in errors)
        raise SchemaValidationError(messages)

