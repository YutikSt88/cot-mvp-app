from __future__ import annotations
import pandas as pd


def run_qa(df: pd.DataFrame, expected_market_keys: set[str], expected_contract_codes: set[str]) -> list[str]:
    """
    Pipeline gate QA checks for canonical dataset.
    
    Returns list of error messages (empty list = PASS).
    """
    errs = []
    
    # 1. Uniqueness: dups (market_key, report_date) == 0
    dup_count = df.duplicated(subset=["market_key", "report_date"]).sum()
    if dup_count > 0:
        errs.append(f"duplicate market_key+report_date rows: {dup_count}")
    
    # 2. Whitelist integrity: market_keys
    actual_market_keys = set(df["market_key"].unique())
    unexpected_market_keys = actual_market_keys - expected_market_keys
    if unexpected_market_keys:
        errs.append(f"unexpected market_key values: {sorted(unexpected_market_keys)}")
    
    # 3. Whitelist integrity: contract_codes
    actual_contract_codes = set(df["contract_code"].unique())
    unexpected_contract_codes = actual_contract_codes - expected_contract_codes
    if unexpected_contract_codes:
        errs.append(f"unexpected contract_code values: {sorted(unexpected_contract_codes)}")
    
    # 4. Null ratio: max_null_ratio <= 0.001 (0.1%) for numeric columns
    numeric_cols = df.select_dtypes(include=["number"]).columns
    max_null_ratio = 0.001
    for col in numeric_cols:
        null_ratio = df[col].isna().mean()
        if null_ratio > max_null_ratio:
            errs.append(f"too many nulls col={col} ratio={null_ratio:.4f}")
    
    # 5. Open interest non-negative: open_interest_all >= 0 (allow 0)
    if "open_interest_all" in df.columns:
        negative_oi = (df["open_interest_all"] < 0).sum()
        if negative_oi > 0:
            errs.append(f"negative open_interest_all detected: {negative_oi} rows")
    
    return errs


# Legacy functions kept for backwards compatibility (not used in Task 2.3)
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
