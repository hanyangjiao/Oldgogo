# Covers: F4
import pytest

from validation.schema_validator import SchemaValidationError, validate_dataset


def test_dataset_schema_valid(repo_root):
    schema_dir = repo_root / "spec" / "schema"
    data = {
        "task_list": [
            {
                "type": "drink_water",
                "start_time": "2026-01-16T09:00:00+08:00",
                "end_time": "2026-01-16T09:05:00+08:00",
                "status": "Incomplete",
                "if_repeatable": True,
            }
        ],
        "anomaly_list": [],
        "last_updated": "2026-01-16T09:05:00+08:00",
    }
    validate_dataset(data, schema_dir)


def test_dataset_schema_invalid(repo_root):
    schema_dir = repo_root / "spec" / "schema"
    data = {"task_list": [{"type": "drink_water"}], "anomaly_list": []}
    with pytest.raises(SchemaValidationError):
        validate_dataset(data, schema_dir)

