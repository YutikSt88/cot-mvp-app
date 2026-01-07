"""Validation functions for compute module."""

from __future__ import annotations

import pandas as pd
import numpy as np


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


def validate_pos_all(df: pd.DataFrame) -> list[str]:
    """
    Validate pos_all columns.
    
    Checks:
    - No NaN values (all must be in [0, 1])
    - All values in [0, 1]
    
    Returns list of error messages.
    """
    errors = []
    groups = ["nc", "comm"]
    sides = ["long", "short", "total"]
    
    for group in groups:
        for side in sides:
            col = f"{group}_{side}_pos_all"
            if col not in df.columns:
                errors.append(f"Missing column: {col}")
                continue
            
            # Check for NaN
            nan_count = df[col].isna().sum()
            if nan_count > 0:
                errors.append(f"{col}: found {nan_count} NaN values (not allowed for pos_all)")
            
            # Check range [0, 1] for non-NaN values
            valid_values = df[col].dropna()
            if len(valid_values) > 0:
                out_of_range = ((valid_values < 0) | (valid_values > 1)).sum()
                if out_of_range > 0:
                    errors.append(f"{col}: {out_of_range} values outside [0, 1] range")
    
    return errors


def validate_pos_5y(df: pd.DataFrame) -> list[str]:
    """
    Validate pos_5y columns.
    
    Checks:
    - NaN allowed (only at start due to min_periods=52)
    - All non-NaN values in [0, 1]
    
    Returns list of error messages.
    """
    errors = []
    groups = ["nc", "comm"]
    sides = ["long", "short", "total"]
    
    for group in groups:
        for side in sides:
            col = f"{group}_{side}_pos_5y"
            if col not in df.columns:
                errors.append(f"Missing column: {col}")
                continue
            
            # Check range [0, 1] for non-NaN values
            valid_values = df[col].dropna()
            if len(valid_values) > 0:
                out_of_range = ((valid_values < 0) | (valid_values > 1)).sum()
                if out_of_range > 0:
                    errors.append(f"{col}: {out_of_range} values outside [0, 1] range")
    
    return errors


def validate_max_min_all(df: pd.DataFrame) -> list[str]:
    """
    Validate that max != min for ALL window (must be 0 rows where max==min).
    
    Returns list of error messages.
    """
    errors = []
    groups = ["nc", "comm"]
    sides = ["long", "short", "total"]
    
    for group in groups:
        for side in sides:
            min_col = f"{group}_{side}_min_all"
            max_col = f"{group}_{side}_max_all"
            
            if min_col not in df.columns or max_col not in df.columns:
                continue
            
            # Check for rows where max == min (both not NaN)
            max_eq_min = (df[min_col] == df[max_col]) & df[min_col].notna() & df[max_col].notna()
            count = max_eq_min.sum()
            if count > 0:
                errors.append(
                    f"ALL window: {count} rows where {min_col} == {max_col} "
                    f"(expected 0 for ALL window)"
                )
    
    return errors


def validate_max_min_5y(df: pd.DataFrame) -> list[str]:
    """
    Validate that max != min for 5Y window (only NaN from min_periods allowed).
    
    Returns list of error messages.
    """
    errors = []
    groups = ["nc", "comm"]
    sides = ["long", "short", "total"]
    
    for group in groups:
        for side in sides:
            min_col = f"{group}_{side}_min_5y"
            max_col = f"{group}_{side}_max_5y"
            
            if min_col not in df.columns or max_col not in df.columns:
                continue
            
            # Check for rows where max == min (both not NaN)
            # This should only happen if both are NaN (due to min_periods)
            max_eq_min = (df[min_col] == df[max_col]) & df[min_col].notna() & df[max_col].notna()
            count = max_eq_min.sum()
            if count > 0:
                    errors.append(
                        f"5Y window: {count} rows where {min_col} == {max_col} "
                        f"(not allowed, only NaN from min_periods allowed)"
                    )
    
    return errors


def validate_chg_1w(df: pd.DataFrame) -> list[str]:
    """
    Validate WoW change columns (*_chg_1w).
    
    Checks:
    1) NaN allowed ONLY for first row per market_key for each *_chg_1w
    2) No inf/-inf; dtype numeric
    3) Formula check on sample rows: chg == current - prev (prev = shift(1) by market_key)
    
    Returns list of error messages.
    """
    errors = []
    groups = ["nc", "comm"]
    sides = ["long", "short", "total"]
    
    # Sort by market_key and report_date for validation
    df_sorted = df.sort_values(["market_key", "report_date"]).reset_index(drop=True)
    
    for group in groups:
        for side in sides:
            col_chg = f"{group}_{side}_chg_1w"
            col_current = f"{group}_{side}"
            
            if col_chg not in df_sorted.columns:
                errors.append(f"Missing column: {col_chg}")
                continue
            
            if col_current not in df_sorted.columns:
                errors.append(f"Missing source column for validation: {col_current}")
                continue
            
            # Check 1: NaN allowed ONLY for first row per market_key
            # Count NaNs per market_key
            for market_key in df_sorted["market_key"].unique():
                market_mask = df_sorted["market_key"] == market_key
                market_data = df_sorted.loc[market_mask, [col_chg, "report_date"]].sort_values("report_date")
                
                if len(market_data) == 0:
                    continue
                
                nan_mask = market_data[col_chg].isna()
                nan_count = nan_mask.sum()
                
                if nan_count > 1:
                    errors.append(
                        f"{col_chg}: {nan_count} NaN values for market_key '{market_key}' "
                        f"(expected at most 1 NaN for first row)"
                    )
                elif nan_count == 1:
                    # Check that NaN is in the first row (earliest report_date)
                    first_idx = market_data.index[0]
                    if not pd.isna(market_data.loc[first_idx, col_chg]):
                        errors.append(
                            f"{col_chg}: NaN not in first row for market_key '{market_key}' "
                            f"(expected NaN only for first row)"
                        )
            
            # Check 2: No inf/-inf; dtype numeric
            if not pd.api.types.is_numeric_dtype(df_sorted[col_chg]):
                errors.append(f"{col_chg}: dtype is not numeric (got {df_sorted[col_chg].dtype})")
            
            # Check for inf/-inf
            if df_sorted[col_chg].dtype in [np.float64, np.float32]:
                inf_mask = np.isinf(df_sorted[col_chg])
                inf_count = inf_mask.sum()
                if inf_count > 0:
                    errors.append(f"{col_chg}: found {inf_count} inf/-inf values (not allowed)")
            
            # Check 3: Formula check on sample rows (non-NaN rows only)
            # chg == current - prev_week (where prev_week = shift(1) within market_key)
            non_nan_mask = df_sorted[col_chg].notna()
            if non_nan_mask.sum() > 0:
                # Calculate expected change: current - shift(1) within market_key
                expected_chg = df_sorted.groupby("market_key")[col_current].transform(
                    lambda x: x - x.shift(1)
                )
                
                # Compare actual vs expected (only for non-NaN rows)
                actual_chg = df_sorted.loc[non_nan_mask, col_chg]
                expected_chg_subset = expected_chg.loc[non_nan_mask]
                
                # Allow small floating point differences (1e-6)
                diff = np.abs(actual_chg - expected_chg_subset)
                mismatch_mask = diff > 1e-6
                mismatch_count = mismatch_mask.sum()
                
                if mismatch_count > 0:
                    errors.append(
                        f"{col_chg}: {mismatch_count} rows where formula mismatch "
                        f"(chg != current - prev_week) - max diff: {diff.max():.2e}"
                    )
    
    return errors


def validate_net_metrics(df: pd.DataFrame) -> list[str]:
    """
    Validate net exposure metrics.
    
    Checks:
    1) All 6 columns exist: nc_net, comm_net, nc_net_chg_1w, comm_net_chg_1w, spec_vs_hedge_net, spec_vs_hedge_net_chg_1w
    2) Formula checks (strict):
       - nc_net == nc_long - nc_short
       - comm_net == comm_long - comm_short
       - spec_vs_hedge_net == nc_net - comm_net
    3) No NaN in nc_net, comm_net, spec_vs_hedge_net
    4) *_chg_1w NaN allowed only for first row per market_key
    5) No inf/-inf in new columns
    
    Returns list of error messages.
    """
    errors = []
    
    # Required columns
    required_cols = [
        "nc_net", "comm_net",
        "nc_net_chg_1w", "comm_net_chg_1w",
        "spec_vs_hedge_net", "spec_vs_hedge_net_chg_1w"
    ]
    
    # Check 1: All columns exist
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing net metrics columns: {', '.join(sorted(missing_cols))}")
        return errors  # Early return if columns are missing
    
    # Sort by market_key and report_date for validation
    df_sorted = df.sort_values(["market_key", "report_date"]).reset_index(drop=True)
    
    # Check 2: Formula checks (strict)
    # nc_net == nc_long - nc_short
    if "nc_long" in df_sorted.columns and "nc_short" in df_sorted.columns:
        expected_nc_net = df_sorted["nc_long"] - df_sorted["nc_short"]
        diff_nc_net = np.abs(df_sorted["nc_net"] - expected_nc_net)
        max_diff = diff_nc_net.max()
        if max_diff > 1e-6:
            errors.append(
                f"nc_net formula mismatch: max diff = {max_diff:.2e} "
                f"(expected: nc_net == nc_long - nc_short)"
            )
    else:
        errors.append("Missing source columns for nc_net validation: nc_long, nc_short")
    
    # comm_net == comm_long - comm_short
    if "comm_long" in df_sorted.columns and "comm_short" in df_sorted.columns:
        expected_comm_net = df_sorted["comm_long"] - df_sorted["comm_short"]
        diff_comm_net = np.abs(df_sorted["comm_net"] - expected_comm_net)
        max_diff = diff_comm_net.max()
        if max_diff > 1e-6:
            errors.append(
                f"comm_net formula mismatch: max diff = {max_diff:.2e} "
                f"(expected: comm_net == comm_long - comm_short)"
            )
    else:
        errors.append("Missing source columns for comm_net validation: comm_long, comm_short")
    
    # spec_vs_hedge_net == nc_net - comm_net
    expected_spec_vs_hedge = df_sorted["nc_net"] - df_sorted["comm_net"]
    diff_spec_vs_hedge = np.abs(df_sorted["spec_vs_hedge_net"] - expected_spec_vs_hedge)
    max_diff = diff_spec_vs_hedge.max()
    if max_diff > 1e-6:
        errors.append(
            f"spec_vs_hedge_net formula mismatch: max diff = {max_diff:.2e} "
            f"(expected: spec_vs_hedge_net == nc_net - comm_net)"
        )
    
    # Check 3: No NaN in nc_net, comm_net, spec_vs_hedge_net
    for col in ["nc_net", "comm_net", "spec_vs_hedge_net"]:
        nan_count = df_sorted[col].isna().sum()
        if nan_count > 0:
            errors.append(f"{col}: found {nan_count} NaN values (not allowed)")
    
    # Check 4: *_chg_1w NaN allowed only for first row per market_key
    chg_cols = ["nc_net_chg_1w", "comm_net_chg_1w", "spec_vs_hedge_net_chg_1w"]
    for col_chg in chg_cols:
        for market_key in df_sorted["market_key"].unique():
            market_mask = df_sorted["market_key"] == market_key
            market_data = df_sorted.loc[market_mask, [col_chg, "report_date"]].sort_values("report_date")
            
            if len(market_data) == 0:
                continue
            
            nan_mask = market_data[col_chg].isna()
            nan_count = nan_mask.sum()
            
            if nan_count > 1:
                errors.append(
                    f"{col_chg}: {nan_count} NaN values for market_key '{market_key}' "
                    f"(expected at most 1 NaN for first row)"
                )
            elif nan_count == 1:
                # Check that NaN is in the first row (earliest report_date)
                first_idx = market_data.index[0]
                if not pd.isna(market_data.loc[first_idx, col_chg]):
                    errors.append(
                        f"{col_chg}: NaN not in first row for market_key '{market_key}' "
                        f"(expected NaN only for first row)"
                    )
    
    # Check 5: No inf/-inf in new columns
    for col in required_cols:
        if not pd.api.types.is_numeric_dtype(df_sorted[col]):
            errors.append(f"{col}: dtype is not numeric (got {df_sorted[col].dtype})")
            continue
        
        if df_sorted[col].dtype in [np.float64, np.float32]:
            inf_mask = np.isinf(df_sorted[col])
            inf_count = inf_mask.sum()
            if inf_count > 0:
                errors.append(f"{col}: found {inf_count} inf/-inf values (not allowed)")
    
    # Check rebalance decomposition metrics
    errors.extend(validate_rebalance_metrics(df))
    
    # Check net side and magnitude gap metrics
    errors.extend(validate_net_side_and_mag_gap(df))
    
    return errors


def validate_net_side_and_mag_gap(df: pd.DataFrame) -> list[str]:
    """
    Validate net side indicators and magnitude gap metrics.
    
    Checks:
    1) All required columns exist
    2) net_mag_gap exact formula check: abs(nc_net) - abs(comm_net)
    3) net_mag_gap_chg_1w equals diff check (tolerance 1e-6)
    4) net_mag_gap_max_abs_5y >= abs(net_mag_gap) where not NaN
    5) net_mag_gap_pos_5y in [0, 1] where not NaN
    6) nc_net_side/comm_net_side only in {"NET_LONG", "NET_SHORT", "FLAT"}
    7) net_alignment only in {"SAME_SIDE", "OPPOSITE_SIDE", "UNKNOWN"}
    
    Returns list of error messages.
    """
    errors = []
    
    # Required columns
    required_cols = [
        "nc_net_side", "comm_net_side", "net_alignment",
        "net_mag_gap", "net_mag_gap_chg_1w",
        "net_mag_gap_max_abs_5y", "net_mag_gap_pos_5y"
    ]
    
    # Check 1: All columns exist
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing net side/magnitude gap columns: {', '.join(sorted(missing_cols))}")
        return errors  # Early return if columns are missing
    
    # Sort by market_key and report_date for validation
    df_sorted = df.sort_values(["market_key", "report_date"]).reset_index(drop=True)
    
    # Check 2: net_mag_gap formula check
    if "nc_net" in df_sorted.columns and "comm_net" in df_sorted.columns:
        expected_mag_gap = np.abs(df_sorted["nc_net"]) - np.abs(df_sorted["comm_net"])
        diff_mag_gap = np.abs(df_sorted["net_mag_gap"] - expected_mag_gap)
        max_diff = diff_mag_gap.max()
        if max_diff > 1e-6:
            errors.append(
                f"net_mag_gap formula mismatch: max diff = {max_diff:.2e} "
                f"(expected: net_mag_gap == abs(nc_net) - abs(comm_net))"
            )
    else:
        errors.append("Missing source columns for net_mag_gap validation: nc_net, comm_net")
    
    # Check 3: net_mag_gap_chg_1w equals diff check
    if "net_mag_gap" in df_sorted.columns:
        expected_chg = df_sorted.groupby("market_key")["net_mag_gap"].transform(
            lambda x: x - x.shift(1)
        )
        # Compare only non-NaN rows
        mask = df_sorted["net_mag_gap_chg_1w"].notna() & expected_chg.notna()
        if mask.sum() > 0:
            diff_chg = np.abs(df_sorted.loc[mask, "net_mag_gap_chg_1w"] - expected_chg.loc[mask])
            max_diff = diff_chg.max()
            if max_diff > 1e-6:
                errors.append(
                    f"net_mag_gap_chg_1w formula mismatch: max diff = {max_diff:.2e} "
                    f"(expected: net_mag_gap_chg_1w == net_mag_gap - shift(1))"
                )
    
    # Check 4: net_mag_gap_max_abs_5y >= abs(net_mag_gap) where not NaN
    mask_max = df_sorted["net_mag_gap_max_abs_5y"].notna() & df_sorted["net_mag_gap"].notna()
    if mask_max.sum() > 0:
        abs_mag_gap = np.abs(df_sorted.loc[mask_max, "net_mag_gap"])
        max_abs_5y = df_sorted.loc[mask_max, "net_mag_gap_max_abs_5y"]
        violation = (max_abs_5y < abs_mag_gap).sum()
        if violation > 0:
            errors.append(
                f"net_mag_gap_max_abs_5y: {violation} rows where max_abs_5y < abs(net_mag_gap) "
                f"(max_abs_5y must be >= abs(net_mag_gap))"
            )
    
    # Check 5: net_mag_gap_pos_5y in [0, 1] where not NaN
    mask_pos = df_sorted["net_mag_gap_pos_5y"].notna()
    if mask_pos.sum() > 0:
        pos_values = df_sorted.loc[mask_pos, "net_mag_gap_pos_5y"]
        out_of_range = ((pos_values < 0) | (pos_values > 1)).sum()
        if out_of_range > 0:
            errors.append(
                f"net_mag_gap_pos_5y: {out_of_range} values outside [0, 1] range "
                f"(min: {pos_values.min():.6f}, max: {pos_values.max():.6f})"
            )
    
    # Check 6: nc_net_side/comm_net_side only in {"NET_LONG", "NET_SHORT", "FLAT"}
    valid_sides = {"NET_LONG", "NET_SHORT", "FLAT"}
    for col in ["nc_net_side", "comm_net_side"]:
        invalid = set(df_sorted[col].unique()) - valid_sides
        if invalid:
            errors.append(
                f"{col}: invalid values found: {sorted(invalid)} "
                f"(allowed: {sorted(valid_sides)})"
            )
    
    # Check 7: net_alignment only in {"SAME_SIDE", "OPPOSITE_SIDE", "UNKNOWN"}
    valid_alignments = {"SAME_SIDE", "OPPOSITE_SIDE", "UNKNOWN"}
    invalid_alignments = set(df_sorted["net_alignment"].unique()) - valid_alignments
    if invalid_alignments:
        errors.append(
            f"net_alignment: invalid values found: {sorted(invalid_alignments)} "
            f"(allowed: {sorted(valid_alignments)})"
        )
    
    # Check net flip flags
    errors.extend(validate_net_flip_flags(df))
    
    return errors


def validate_net_flip_flags(df: pd.DataFrame) -> list[str]:
    """
    Validate net flip flags (sign change detection).
    
    Checks:
    1) All required columns exist
    2) Type check: bool or 0/1 int, values only in {True, False} or {0, 1}
    3) Formula check: flip = (prev != 0) AND (curr != 0) AND (sign(curr) != sign(prev))
    
    Returns list of error messages.
    """
    errors = []
    
    # Required columns
    required_cols = [
        "nc_net_flip_1w",
        "comm_net_flip_1w",
        "spec_vs_hedge_net_flip_1w"
    ]
    
    # Check 1: All columns exist
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing net flip columns: {', '.join(sorted(missing_cols))}")
        return errors  # Early return if columns are missing
    
    # Sort by market_key and report_date for validation
    df_sorted = df.sort_values(["market_key", "report_date"]).reset_index(drop=True)
    
    # Check 2: Type and value check
    for col in required_cols:
        unique_vals = set(df_sorted[col].dropna().unique())
        # Allow bool or 0/1 int
        valid_vals = {True, False, 0, 1}
        invalid_vals = unique_vals - valid_vals
        if invalid_vals:
            errors.append(
                f"{col}: invalid values found: {sorted(invalid_vals)} "
                f"(allowed: {sorted(valid_vals)})"
            )
    
    # Check 3: Formula check - reproduce expected flip
    def sign_func(val):
        """Sign function: 1 if >0, -1 if <0, 0 if ==0 or NaN."""
        if pd.isna(val):
            return 0
        if val > 0:
            return 1
        elif val < 0:
            return -1
        else:
            return 0
    
    # Check nc_net_flip_1w
    if "nc_net" in df_sorted.columns:
        prev_nc = df_sorted.groupby("market_key")["nc_net"].shift(1)
        curr_nc = df_sorted["nc_net"]
        
        prev_sign = prev_nc.apply(sign_func)
        curr_sign = curr_nc.apply(sign_func)
        
        expected_flip = (prev_sign != 0) & (curr_sign != 0) & (curr_sign != prev_sign)
        expected_flip = expected_flip.fillna(False).astype(bool)
        
        actual_flip = df_sorted["nc_net_flip_1w"].fillna(False).astype(bool)
        
        mismatch = (expected_flip != actual_flip).sum()
        if mismatch > 0:
            errors.append(
                f"nc_net_flip_1w formula mismatch: {mismatch} rows where expected != actual"
            )
    
    # Check comm_net_flip_1w
    if "comm_net" in df_sorted.columns:
        prev_comm = df_sorted.groupby("market_key")["comm_net"].shift(1)
        curr_comm = df_sorted["comm_net"]
        
        prev_sign = prev_comm.apply(sign_func)
        curr_sign = curr_comm.apply(sign_func)
        
        expected_flip = (prev_sign != 0) & (curr_sign != 0) & (curr_sign != prev_sign)
        expected_flip = expected_flip.fillna(False).astype(bool)
        
        actual_flip = df_sorted["comm_net_flip_1w"].fillna(False).astype(bool)
        
        mismatch = (expected_flip != actual_flip).sum()
        if mismatch > 0:
            errors.append(
                f"comm_net_flip_1w formula mismatch: {mismatch} rows where expected != actual"
            )
    
    # Check spec_vs_hedge_net_flip_1w
    if "spec_vs_hedge_net" in df_sorted.columns:
        prev_spec = df_sorted.groupby("market_key")["spec_vs_hedge_net"].shift(1)
        curr_spec = df_sorted["spec_vs_hedge_net"]
        
        prev_sign = prev_spec.apply(sign_func)
        curr_sign = curr_spec.apply(sign_func)
        
        expected_flip = (prev_sign != 0) & (curr_sign != 0) & (curr_sign != prev_sign)
        expected_flip = expected_flip.fillna(False).astype(bool)
        
        actual_flip = df_sorted["spec_vs_hedge_net_flip_1w"].fillna(False).astype(bool)
        
        mismatch = (expected_flip != actual_flip).sum()
        if mismatch > 0:
            errors.append(
                f"spec_vs_hedge_net_flip_1w formula mismatch: {mismatch} rows where expected != actual"
            )
    
    return errors


def validate_rebalance_metrics(df: pd.DataFrame) -> list[str]:
    """
    Validate rebalance decomposition metrics.
    
    Checks:
    1) All 8 columns exist
    2) No inf/-inf in new columns
    3) Invariants: nc_net_chg_1w == nc_long_chg_1w - nc_short_chg_1w (and comm)
    4) Mathematical constraints: rebalance >= 0, rebalance == gross - net_abs
    5) Share bounds: 0 <= rebalance_share <= 1 (for gross > 0), NaN for gross == 0
    
    Returns list of error messages.
    """
    errors = []
    
    # Required columns
    required_cols = [
        "nc_gross_chg_1w", "nc_net_abs_chg_1w", "nc_rebalance_chg_1w", "nc_rebalance_share_1w",
        "comm_gross_chg_1w", "comm_net_abs_chg_1w", "comm_rebalance_chg_1w", "comm_rebalance_share_1w"
    ]
    
    # Check 1: All columns exist
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing rebalance metrics columns: {', '.join(sorted(missing_cols))}")
        return errors  # Early return if columns are missing
    
    # Sort by market_key and report_date for validation
    df_sorted = df.sort_values(["market_key", "report_date"]).reset_index(drop=True)
    
    # Check 2: No inf/-inf in new columns + net_chg_1w columns
    inf_check_cols = required_cols + ["nc_net_chg_1w", "comm_net_chg_1w"]
    for col in inf_check_cols:
        if col not in df_sorted.columns:
            continue
        if not pd.api.types.is_numeric_dtype(df_sorted[col]):
            errors.append(f"{col}: dtype is not numeric (got {df_sorted[col].dtype})")
            continue
        if df_sorted[col].dtype in [np.float64, np.float32]:
            inf_mask = np.isinf(df_sorted[col])
            inf_count = inf_mask.sum()
            if inf_count > 0:
                errors.append(f"{col}: found {inf_count} inf/-inf values (not allowed)")
    
    # Check 3: Invariants (net_chg_1w == long_chg_1w - short_chg_1w)
    tol = 1e-9
    
    # nc_net_chg_1w == nc_long_chg_1w - nc_short_chg_1w
    if all(col in df_sorted.columns for col in ["nc_long_chg_1w", "nc_short_chg_1w", "nc_net_chg_1w"]):
        nc_mask = df_sorted["nc_long_chg_1w"].notna() & df_sorted["nc_short_chg_1w"].notna() & df_sorted["nc_net_chg_1w"].notna()
        if nc_mask.sum() > 0:
            expected_nc_net_chg = df_sorted.loc[nc_mask, "nc_long_chg_1w"] - df_sorted.loc[nc_mask, "nc_short_chg_1w"]
            actual_nc_net_chg = df_sorted.loc[nc_mask, "nc_net_chg_1w"]
            diff_nc = np.abs(actual_nc_net_chg - expected_nc_net_chg)
            max_diff = diff_nc.max()
            if max_diff > tol:
                errors.append(
                    f"nc_net_chg_1w invariant mismatch: max diff = {max_diff:.2e} "
                    f"(expected: nc_net_chg_1w == nc_long_chg_1w - nc_short_chg_1w)"
                )
    
    # comm_net_chg_1w == comm_long_chg_1w - comm_short_chg_1w
    if all(col in df_sorted.columns for col in ["comm_long_chg_1w", "comm_short_chg_1w", "comm_net_chg_1w"]):
        comm_mask = df_sorted["comm_long_chg_1w"].notna() & df_sorted["comm_short_chg_1w"].notna() & df_sorted["comm_net_chg_1w"].notna()
        if comm_mask.sum() > 0:
            expected_comm_net_chg = df_sorted.loc[comm_mask, "comm_long_chg_1w"] - df_sorted.loc[comm_mask, "comm_short_chg_1w"]
            actual_comm_net_chg = df_sorted.loc[comm_mask, "comm_net_chg_1w"]
            diff_comm = np.abs(actual_comm_net_chg - expected_comm_net_chg)
            max_diff = diff_comm.max()
            if max_diff > tol:
                errors.append(
                    f"comm_net_chg_1w invariant mismatch: max diff = {max_diff:.2e} "
                    f"(expected: comm_net_chg_1w == comm_long_chg_1w - comm_short_chg_1w)"
                )
    
    # Check 4: Mathematical constraints (for nc and comm)
    for prefix in ["nc", "comm"]:
        gross_col = f"{prefix}_gross_chg_1w"
        net_abs_col = f"{prefix}_net_abs_chg_1w"
        rebalance_col = f"{prefix}_rebalance_chg_1w"
        share_col = f"{prefix}_rebalance_share_1w"
        
        # Non-NaN mask for required fields
        mask = (
            df_sorted[gross_col].notna() &
            df_sorted[net_abs_col].notna() &
            df_sorted[rebalance_col].notna()
        )
        
        if mask.sum() > 0:
            gross = df_sorted.loc[mask, gross_col]
            net_abs = df_sorted.loc[mask, net_abs_col]
            rebalance = df_sorted.loc[mask, rebalance_col]
            
            # gross >= 0
            if (gross < 0).any():
                errors.append(f"{gross_col}: found negative values (must be >= 0)")
            
            # net_abs >= 0
            if (net_abs < 0).any():
                errors.append(f"{net_abs_col}: found negative values (must be >= 0)")
            
            # rebalance >= 0 (with tolerance)
            if (rebalance < -tol).any():
                errors.append(f"{rebalance_col}: found values < -{tol} (must be >= 0)")
            
            # rebalance == gross - net_abs (with tolerance)
            expected_rebalance = gross - net_abs
            diff_rebalance = np.abs(rebalance - expected_rebalance)
            max_diff = diff_rebalance.max()
            if max_diff > tol:
                errors.append(
                    f"{rebalance_col} formula mismatch: max diff = {max_diff:.2e} "
                    f"(expected: {rebalance_col} == {gross_col} - {net_abs_col})"
                )
            
            # Check 5: Share bounds
            # For gross > 0: 0 <= rebalance_share <= 1
            gross_pos_mask = mask & (df_sorted[gross_col] > 0)
            if gross_pos_mask.sum() > 0:
                share_values = df_sorted.loc[gross_pos_mask, share_col]
                # Check for NaN where gross > 0 (should not happen)
                nan_count = share_values.isna().sum()
                if nan_count > 0:
                    errors.append(f"{share_col}: found {nan_count} NaN values where {gross_col} > 0 (not allowed)")
                
                # Check bounds [0, 1]
                valid_share = share_values.dropna()
                if len(valid_share) > 0:
                    out_of_range = ((valid_share < -tol) | (valid_share > 1 + tol)).sum()
                    if out_of_range > 0:
                        errors.append(
                            f"{share_col}: {out_of_range} values outside [0, 1] range "
                            f"(min: {valid_share.min():.6f}, max: {valid_share.max():.6f})"
                        )
            
            # For gross == 0: rebalance_share must be NaN
            gross_zero_mask = mask & (df_sorted[gross_col] == 0)
            if gross_zero_mask.sum() > 0:
                share_values_zero = df_sorted.loc[gross_zero_mask, share_col]
                nan_count_zero = share_values_zero.isna().sum()
                non_nan_count = (gross_zero_mask.sum() - nan_count_zero)
                if non_nan_count > 0:
                    errors.append(
                        f"{share_col}: found {non_nan_count} non-NaN values where {gross_col} == 0 "
                        f"(must be NaN)"
                    )
    
    return errors


def validate_oi_metrics(df: pd.DataFrame) -> list[str]:
    """
    Validate Open Interest metrics.
    
    Checks:
    1) All required columns exist: open_interest, open_interest_chg_1w, open_interest_pos_all, open_interest_pos_5y
    2) open_interest >= 0 (no negative values)
    3) open_interest_pos_all: no NaN, all values in [0, 1]
    4) open_interest_pos_5y: NaN allowed (only at start due to min_periods=52), non-NaN in [0, 1]
    5) open_interest_chg_1w: NaN allowed only for first row per market_key
    6) No inf/-inf in OI columns
    
    Returns list of error messages.
    """
    errors = []
    
    # Required columns
    required_cols = [
        "open_interest",
        "open_interest_chg_1w",
        "open_interest_chg_1w_pct",
        "open_interest_pos_all",
        "open_interest_pos_5y"
    ]
    
    # Check 1: All columns exist
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing OI metrics columns: {', '.join(sorted(missing_cols))}")
        return errors  # Early return if columns are missing
    
    # Sort by market_key and report_date for validation
    df_sorted = df.sort_values(["market_key", "report_date"]).reset_index(drop=True)
    
    # Check 2: open_interest >= 0
    negative_oi = (df_sorted["open_interest"] < 0).sum()
    if negative_oi > 0:
        errors.append(f"open_interest: found {negative_oi} negative values (must be >= 0)")
    
    # Check 3: open_interest_pos_all: no NaN, all values in [0, 1]
    nan_count_all = df_sorted["open_interest_pos_all"].isna().sum()
    if nan_count_all > 0:
        errors.append(f"open_interest_pos_all: found {nan_count_all} NaN values (not allowed for pos_all)")
    
    valid_pos_all = df_sorted["open_interest_pos_all"].dropna()
    if len(valid_pos_all) > 0:
        out_of_range = ((valid_pos_all < 0) | (valid_pos_all > 1)).sum()
        if out_of_range > 0:
            errors.append(f"open_interest_pos_all: {out_of_range} values outside [0, 1] range")
    
    # Check 4: open_interest_pos_5y: NaN allowed, non-NaN in [0, 1]
    valid_pos_5y = df_sorted["open_interest_pos_5y"].dropna()
    if len(valid_pos_5y) > 0:
        out_of_range = ((valid_pos_5y < 0) | (valid_pos_5y > 1)).sum()
        if out_of_range > 0:
            errors.append(f"open_interest_pos_5y: {out_of_range} values outside [0, 1] range")
    
    # Check 5: open_interest_chg_1w: NaN allowed only for first row per market_key
    for market_key in df_sorted["market_key"].unique():
        market_mask = df_sorted["market_key"] == market_key
        market_data = df_sorted.loc[market_mask, ["open_interest_chg_1w", "report_date"]].sort_values("report_date")
        
        if len(market_data) == 0:
            continue
        
        nan_mask = market_data["open_interest_chg_1w"].isna()
        nan_count = nan_mask.sum()
        
        if nan_count > 1:
            errors.append(
                f"open_interest_chg_1w: {nan_count} NaN values for market_key '{market_key}' "
                f"(expected at most 1 NaN for first row)"
            )
        elif nan_count == 1:
            # Check that NaN is in the first row (earliest report_date)
            first_idx = market_data.index[0]
            if not pd.isna(market_data.loc[first_idx, "open_interest_chg_1w"]):
                errors.append(
                    f"open_interest_chg_1w: NaN not in first row for market_key '{market_key}' "
                    f"(expected NaN only for first row)"
                )
    
    # Check 6: open_interest_chg_1w_pct: no inf/-inf
    if "open_interest_chg_1w_pct" in df_sorted.columns:
        if df_sorted["open_interest_chg_1w_pct"].dtype in [np.float64, np.float32]:
            inf_mask = np.isinf(df_sorted["open_interest_chg_1w_pct"])
            inf_count = inf_mask.sum()
            if inf_count > 0:
                errors.append(f"open_interest_chg_1w_pct: found {inf_count} inf/-inf values (not allowed)")
    
    # Check 7: No inf/-inf in OI columns
    for col in required_cols:
        if col == "open_interest_chg_1w_pct":
            continue  # Already checked above
        if not pd.api.types.is_numeric_dtype(df_sorted[col]):
            errors.append(f"{col}: dtype is not numeric (got {df_sorted[col].dtype})")
            continue
        
        if df_sorted[col].dtype in [np.float64, np.float32]:
            inf_mask = np.isinf(df_sorted[col])
            inf_count = inf_mask.sum()
            if inf_count > 0:
                errors.append(f"{col}: found {inf_count} inf/-inf values (not allowed)")
    
    return errors


def validate_exposure_shares(df: pd.DataFrame) -> list[str]:
    """
    Validate gross exposure share metrics.
    
    Checks:
    1) Always required: funds_gross, comm_gross, funds_gross_share, comm_gross_share,
       funds_gross_share_chg_1w_pp, comm_gross_share_chg_1w_pp
    2) Conditionally required: NR columns ONLY if nr_long/nr_short exist in canonical
    3) Shares should be within [0, 1] when not NaN
    4) pp changes should be finite (allow NaN)
    5) If NR exists: funds_share + comm_share + nr_share close to 1.0 (tolerance 1e-6) when not NaN
    6) No inf/-inf
    
    Returns list of error messages.
    """
    errors = []
    
    # Always required columns
    required_cols = [
        "funds_gross",
        "comm_gross",
        "funds_gross_share",
        "comm_gross_share",
        "funds_gross_share_chg_1w_pp",
        "comm_gross_share_chg_1w_pp"
    ]
    
    # Check 1: Always required columns exist
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing required exposure share columns: {', '.join(sorted(missing_cols))}")
        return errors  # Early return if required columns are missing
    
    # Check if NR columns exist (conditional requirement)
    has_nr = "nr_gross" in df.columns and "nr_gross_share" in df.columns and "nr_gross_share_chg_1w_pp" in df.columns
    
    # Sort by market_key and report_date for validation
    df_sorted = df.sort_values(["market_key", "report_date"]).reset_index(drop=True)
    
    # Check 2: Shares should be within [0, 1] when not NaN
    for share_col in ["funds_gross_share", "comm_gross_share"]:
        valid_values = df_sorted[share_col].dropna()
        if len(valid_values) > 0:
            out_of_range = ((valid_values < 0) | (valid_values > 1)).sum()
            if out_of_range > 0:
                errors.append(
                    f"{share_col}: {out_of_range} values outside [0, 1] range "
                    f"(min: {valid_values.min():.6f}, max: {valid_values.max():.6f})"
                )
    
    if has_nr:
        valid_nr_share = df_sorted["nr_gross_share"].dropna()
        if len(valid_nr_share) > 0:
            out_of_range = ((valid_nr_share < 0) | (valid_nr_share > 1)).sum()
            if out_of_range > 0:
                errors.append(
                    f"nr_gross_share: {out_of_range} values outside [0, 1] range "
                    f"(min: {valid_nr_share.min():.6f}, max: {valid_nr_share.max():.6f})"
                )
    
    # Check 3: pp changes should be finite (allow NaN)
    for pp_col in ["funds_gross_share_chg_1w_pp", "comm_gross_share_chg_1w_pp"]:
        if not pd.api.types.is_numeric_dtype(df_sorted[pp_col]):
            errors.append(f"{pp_col}: dtype is not numeric (got {df_sorted[pp_col].dtype})")
            continue
        
        if df_sorted[pp_col].dtype in [np.float64, np.float32]:
            inf_mask = np.isinf(df_sorted[pp_col])
            inf_count = inf_mask.sum()
            if inf_count > 0:
                errors.append(f"{pp_col}: found {inf_count} inf/-inf values (not allowed)")
    
    if has_nr:
        if not pd.api.types.is_numeric_dtype(df_sorted["nr_gross_share_chg_1w_pp"]):
            errors.append(f"nr_gross_share_chg_1w_pp: dtype is not numeric (got {df_sorted['nr_gross_share_chg_1w_pp'].dtype})")
        elif df_sorted["nr_gross_share_chg_1w_pp"].dtype in [np.float64, np.float32]:
            inf_mask = np.isinf(df_sorted["nr_gross_share_chg_1w_pp"])
            inf_count = inf_mask.sum()
            if inf_count > 0:
                errors.append(f"nr_gross_share_chg_1w_pp: found {inf_count} inf/-inf values (not allowed)")
    
    # Check 4: If NR exists: funds_share + comm_share + nr_share close to 1.0 (tolerance 1e-6) when not NaN
    if has_nr:
        # Check rows where all three shares are not NaN
        mask_all = (
            df_sorted["funds_gross_share"].notna() &
            df_sorted["comm_gross_share"].notna() &
            df_sorted["nr_gross_share"].notna()
        )
        if mask_all.sum() > 0:
            share_sum = (
                df_sorted.loc[mask_all, "funds_gross_share"] +
                df_sorted.loc[mask_all, "comm_gross_share"] +
                df_sorted.loc[mask_all, "nr_gross_share"]
            )
            diff_from_one = np.abs(share_sum - 1.0)
            tolerance = 1e-6
            violations = (diff_from_one > tolerance).sum()
            if violations > 0:
                max_diff = diff_from_one.max()
                errors.append(
                    f"Exposure shares sum: {violations} rows where "
                    f"funds_share + comm_share + nr_share != 1.0 (tolerance {tolerance}) "
                    f"(max diff: {max_diff:.2e})"
                )
    else:
        # Without NR: funds_share + comm_share should sum to 1.0
        mask_both = (
            df_sorted["funds_gross_share"].notna() &
            df_sorted["comm_gross_share"].notna()
        )
        if mask_both.sum() > 0:
            share_sum = (
                df_sorted.loc[mask_both, "funds_gross_share"] +
                df_sorted.loc[mask_both, "comm_gross_share"]
            )
            diff_from_one = np.abs(share_sum - 1.0)
            tolerance = 1e-6
            violations = (diff_from_one > tolerance).sum()
            if violations > 0:
                max_diff = diff_from_one.max()
                errors.append(
                    f"Exposure shares sum: {violations} rows where "
                    f"funds_share + comm_share != 1.0 (tolerance {tolerance}) "
                    f"(max diff: {max_diff:.2e})"
                )
    
    # Check 5: No inf/-inf in gross columns
    for col in ["funds_gross", "comm_gross"]:
        if not pd.api.types.is_numeric_dtype(df_sorted[col]):
            errors.append(f"{col}: dtype is not numeric (got {df_sorted[col].dtype})")
            continue
        
        if df_sorted[col].dtype in [np.float64, np.float32]:
            inf_mask = np.isinf(df_sorted[col])
            inf_count = inf_mask.sum()
            if inf_count > 0:
                errors.append(f"{col}: found {inf_count} inf/-inf values (not allowed)")
    
    if has_nr:
        if not pd.api.types.is_numeric_dtype(df_sorted["nr_gross"]):
            errors.append(f"nr_gross: dtype is not numeric (got {df_sorted['nr_gross'].dtype})")
        elif df_sorted["nr_gross"].dtype in [np.float64, np.float32]:
            inf_mask = np.isinf(df_sorted["nr_gross"])
            inf_count = inf_mask.sum()
            if inf_count > 0:
                errors.append(f"nr_gross: found {inf_count} inf/-inf values (not allowed)")
    
    return errors
