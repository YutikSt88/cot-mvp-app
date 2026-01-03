from __future__ import annotations
import pandas as pd

def qa_uniqueness(df: pd.DataFrame) -> list[str]:
    errs = []
    dup = df.duplicated(subset=["market_key", "report_date"]).sum()
    if dup > 0:
        errs.append(f"duplicate market_key+report_date rows: {dup}")
    return errs

def qa_nulls(df: pd.DataFrame, max_null_ratio: float = 0.001) -> list[str]:
    errs = []
    ratio = df.isna().mean()
    bad = ratio[ratio > max_null_ratio]
    for col, r in bad.items():
        errs.append(f"too many nulls col={col} ratio={r:.4f}")
    return errs

def qa_open_interest(df: pd.DataFrame) -> list[str]:
    errs = []
    if (df["open_interest_all"] < 0).any():
        errs.append("negative open_interest_all detected")
    return errs
