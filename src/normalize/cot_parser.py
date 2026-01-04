from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import zipfile
import pandas as pd
from io import BytesIO


@dataclass(frozen=True)
class ParsedLegacy:
    df: pd.DataFrame
    source_year: int
    source_file: str


def parse_deacot_zip(zip_path: Path, year: int) -> ParsedLegacy:
    """
    Parse annual.txt from COT ZIP archive.
    
    Reads annual.txt specifically (comma-separated, UTF-8 encoding).
    Ensures correct column mapping: different trader groups read from different columns.
    """
    with zipfile.ZipFile(zip_path, "r") as z:
        # Look for annual.txt specifically
        if "annual.txt" not in z.namelist():
            raise ValueError(f"annual.txt not found inside {zip_path.name}")
        
        raw = z.read("annual.txt")
        bio = BytesIO(raw)
        df = pd.read_csv(bio, encoding="utf-8", delimiter=",", low_memory=False)
        df.columns = [c.strip() for c in df.columns]
        
        # Find correct columns for each trader group with specific matching
        # This fixes the issue where comm_long == nc_long (they read from same column)
        def find_column_for_group(group_keywords: list[str], exclude_keywords: list[str] = None) -> str | None:
            """Find column matching all keywords and excluding exclude_keywords."""
            exclude_keywords = exclude_keywords or []
            for col in df.columns:
                col_lower = col.lower()
                matches_all = all(kw.lower() in col_lower for kw in group_keywords)
                matches_none_exclude = not any(kw.lower() in col_lower for kw in exclude_keywords)
                if matches_all and matches_none_exclude:
                    return col
            return None
        
        # Find columns for each group
        comm_long_col = find_column_for_group(["commercial", "positions", "long", "all"], exclude_keywords=["non", "old", "other"])
        comm_short_col = find_column_for_group(["commercial", "positions", "short", "all"], exclude_keywords=["non", "old", "other"])
        nc_long_col = find_column_for_group(["noncommercial", "positions", "long", "all"], exclude_keywords=["old", "other"])
        nc_short_col = find_column_for_group(["noncommercial", "positions", "short", "all"], exclude_keywords=["old", "other"])
        nr_long_col = find_column_for_group(["nonreportable", "positions", "long", "all"], exclude_keywords=["old", "other"])
        nr_short_col = find_column_for_group(["nonreportable", "positions", "short", "all"], exclude_keywords=["old", "other"])
        
        # Verify we found different columns for different groups
        if comm_long_col and nc_long_col and comm_long_col == nc_long_col:
            available_cols = [c for c in df.columns if "position" in c.lower() and "long" in c.lower()]
            raise ValueError(
                f"Column mismatch: comm_long and nc_long both map to '{comm_long_col}' in {zip_path.name}. "
                f"Available columns: {available_cols[:10]}"
            )
        
        if comm_short_col and nc_short_col and comm_short_col == nc_short_col:
            available_cols = [c for c in df.columns if "position" in c.lower() and "short" in c.lower()]
            raise ValueError(
                f"Column mismatch: comm_short and nc_short both map to '{comm_short_col}' in {zip_path.name}. "
                f"Available columns: {available_cols[:10]}"
            )
        
        # Rename columns to canonical format to ensure pick() finds correct ones
        # This fixes the issue where pick() might find same column for different groups
        column_renames = {}
        if comm_long_col:
            # Rename to ensure "Commercial Positions-Long (All)" is unique
            df = df.rename(columns={comm_long_col: "Commercial Positions-Long (All)"})
        if comm_short_col:
            df = df.rename(columns={comm_short_col: "Commercial Positions-Short (All)"})
        if nc_long_col and nc_long_col != comm_long_col:
            # Only rename if different from comm_long_col
            df = df.rename(columns={nc_long_col: "Noncommercial Positions-Long (All)"})
        if nc_short_col and nc_short_col != comm_short_col:
            df = df.rename(columns={nc_short_col: "Noncommercial Positions-Short (All)"})
        if nr_long_col:
            df = df.rename(columns={nr_long_col: "Nonreportable Positions-Long (All)"})
        if nr_short_col:
            df = df.rename(columns={nr_short_col: "Nonreportable Positions-Short (All)"})
        
        # Return DataFrame with normalized column names
        # run_normalize.py pick() function will find the correct columns by exact name match
        return ParsedLegacy(df=df, source_year=year, source_file="annual.txt")
