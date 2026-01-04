"""Validation functions for compute module."""

from __future__ import annotations

import pandas as pd


def validate_canonical_exists(canonical_path: str | None) -> None:
    """Fail if canonical parquet is missing."""
    if canonical_path is None:
        raise FileNotFoundError("Canonical parquet path is None")
    
    from pathlib import Path
    path = Path(canonical_path)
    if not path.exists():
        raise FileNotFoundError(f"Canonical parquet not found: {canonical_path}")


def validate_required_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    """Check for missing required columns. Returns list of error messages."""
    errors = []
    missing = set(required) - set(df.columns)
    if missing:
        available = ", ".join(sorted(df.columns))
        errors.append(
            f"Missing required columns: {', '.join(sorted(missing))}. "
            f"Available columns: {available}"
        )
    return errors


def validate_output_rows(df: pd.DataFrame) -> list[str]:
    """Check that output has rows. Returns list of error messages."""
    errors = []
    if len(df) == 0:
        errors.append("Output has 0 rows")
    return errors


def validate_uniqueness(df: pd.DataFrame, keys: list[str]) -> list[str]:
    """Check for duplicates on key columns. Returns list of error messages."""
    errors = []
    dup_count = df.duplicated(subset=keys).sum()
    if dup_count > 0:
        errors.append(f"Found {dup_count} duplicate rows on keys: {', '.join(keys)}")
    return errors

