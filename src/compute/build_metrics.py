"""Build metrics DataFrame from canonical_full data."""

from __future__ import annotations

import os
import logging

import pandas as pd
import numpy as np

logger = logging.getLogger("cot_mvp")


def build_metrics_weekly(
    canonical: pd.DataFrame,
    market_to_category: dict[str, str],
    market_to_contract: dict[str, str],
) -> pd.DataFrame:
    """
    Build metrics DataFrame with current values and heat-range indicators.
    
    Args:
        canonical: Canonical_full DataFrame with market_key, report_date, comm_long, comm_short, nc_long, nc_short
        market_to_category: Mapping from market_key to category
        market_to_contract: Mapping from market_key to contract_code
    
    Returns:
        DataFrame with columns:
        - Identity: market_key, report_date, contract_code, category
        - Current: nc_long, nc_short, nc_total, comm_long, comm_short, comm_total
        - ALL window: {nc,comm}_{long,short,total}_{min,max,pos}_all
        - 5Y window: {nc,comm}_{long,short,total}_{min,max,pos}_5y
    """
    # Filter to only markets in config
    whitelist_markets = set(market_to_category.keys())
    df = canonical[canonical["market_key"].isin(whitelist_markets)].copy()
    
    # Ensure sorted by market_key and report_date for rolling calculations
    df = df.sort_values(["market_key", "report_date"]).reset_index(drop=True)
    
    # Build identity columns
    metrics = pd.DataFrame({
        "market_key": df["market_key"],
        "report_date": df["report_date"],
        "contract_code": df["contract_code"],
        "category": df["market_key"].map(market_to_category),
    })
    
    # Current values: NC and COMM (long/short/total)
    metrics["nc_long"] = pd.to_numeric(df["nc_long"], errors="coerce")
    metrics["nc_short"] = pd.to_numeric(df["nc_short"], errors="coerce")
    metrics["nc_total"] = metrics["nc_long"] + metrics["nc_short"]
    
    metrics["comm_long"] = pd.to_numeric(df["comm_long"], errors="coerce")
    metrics["comm_short"] = pd.to_numeric(df["comm_short"], errors="coerce")
    metrics["comm_total"] = metrics["comm_long"] + metrics["comm_short"]
    
    # Check if NR columns exist in canonical
    has_nr = "nr_long" in df.columns and "nr_short" in df.columns
    if has_nr:
        metrics["nr_long"] = pd.to_numeric(df["nr_long"], errors="coerce")
        metrics["nr_short"] = pd.to_numeric(df["nr_short"], errors="coerce")
        metrics["nr_total"] = metrics["nr_long"] + metrics["nr_short"]
    
    # Net exposure metrics
    metrics["nc_net"] = metrics["nc_long"] - metrics["nc_short"]
    metrics["comm_net"] = metrics["comm_long"] - metrics["comm_short"]
    metrics["spec_vs_hedge_net"] = metrics["nc_net"] - metrics["comm_net"]
    if has_nr:
        metrics["nr_net"] = metrics["nr_long"] - metrics["nr_short"]
    
    # Open Interest: current value
    metrics["open_interest"] = pd.to_numeric(df["open_interest_all"], errors="coerce")
    
    # Heat-range columns for ALL window and 5Y rolling window
    # Groups: nc, comm, and optionally nr
    # Sides: long, short, total
    groups = ["nc", "comm"]
    if has_nr:
        groups.append("nr")
    sides = ["long", "short", "total"]
    
    # ALL window: min/max/pos across entire history per market_key
    for group in groups:
        for side in sides:
            col_current = f"{group}_{side}"
            
            # Calculate min/max per market_key across all history
            min_all = metrics.groupby("market_key")[col_current].transform("min")
            max_all = metrics.groupby("market_key")[col_current].transform("max")
            
            metrics[f"{group}_{side}_min_all"] = min_all
            metrics[f"{group}_{side}_max_all"] = max_all
            
            # Calculate position: (current - min) / (max - min)
            # If max == min, set to NaN (not 0.5)
            diff = max_all - min_all
            pos_all = np.where(diff > 0, (metrics[col_current] - min_all) / diff, np.nan)
            metrics[f"{group}_{side}_pos_all"] = pos_all
    
    # 5Y rolling window: 260 weeks, min_periods=52
    # Use backward-looking window (default) - includes current row
    for group in groups:
        for side in sides:
            col_current = f"{group}_{side}"
            
            # Rolling min/max per market_key (260 weeks = 5 years, backward-looking)
            # Default closed="right" includes current row in the window
            min_5y = metrics.groupby("market_key")[col_current].transform(
                lambda x: x.rolling(window=260, min_periods=52).min()
            )
            max_5y = metrics.groupby("market_key")[col_current].transform(
                lambda x: x.rolling(window=260, min_periods=52).max()
            )
            
            metrics[f"{group}_{side}_min_5y"] = min_5y
            metrics[f"{group}_{side}_max_5y"] = max_5y
            
            # Calculate position: (current - min_5y) / (max_5y - min_5y)
            # If max_5y == min_5y (and both are not NaN), set to NaN
            diff_5y = max_5y - min_5y
            pos_5y = np.where(
                (diff_5y > 0) & min_5y.notna() & max_5y.notna(),
                (metrics[col_current] - min_5y) / diff_5y,
                np.nan
            )
            metrics[f"{group}_{side}_pos_5y"] = pos_5y
    
    # Open Interest positioning metrics (ALL window and 5Y rolling window)
    # ALL window: min/max/pos across entire history per market_key
    min_oi_all = metrics.groupby("market_key")["open_interest"].transform("min")
    max_oi_all = metrics.groupby("market_key")["open_interest"].transform("max")
    diff_oi_all = max_oi_all - min_oi_all
    pos_oi_all = np.where(diff_oi_all > 0, (metrics["open_interest"] - min_oi_all) / diff_oi_all, np.nan)
    metrics["open_interest_pos_all"] = pos_oi_all
    
    # 5Y rolling window: 260 weeks, min_periods=52
    min_oi_5y = metrics.groupby("market_key")["open_interest"].transform(
        lambda x: x.rolling(window=260, min_periods=52).min()
    )
    max_oi_5y = metrics.groupby("market_key")["open_interest"].transform(
        lambda x: x.rolling(window=260, min_periods=52).max()
    )
    diff_oi_5y = max_oi_5y - min_oi_5y
    pos_oi_5y = np.where(
        (diff_oi_5y > 0) & min_oi_5y.notna() & max_oi_5y.notna(),
        (metrics["open_interest"] - min_oi_5y) / diff_oi_5y,
        np.nan
    )
    metrics["open_interest_pos_5y"] = pos_oi_5y
    
    # WoW absolute change metrics (Δ1w): current - previous week within each market_key
    # NaN for first row per market_key (no previous week)
    for group in groups:
        for side in sides:
            col_current = f"{group}_{side}"
            col_chg = f"{group}_{side}_chg_1w"
            
            # Calculate change: current - previous week (shift(1) within each market_key group)
            prev_week = metrics.groupby("market_key")[col_current].shift(1)
            metrics[col_chg] = metrics[col_current] - prev_week
    
    # WoW change for net metrics
    metrics["nc_net_chg_1w"] = metrics.groupby("market_key")["nc_net"].transform(
        lambda x: x - x.shift(1)
    )
    metrics["comm_net_chg_1w"] = metrics.groupby("market_key")["comm_net"].transform(
        lambda x: x - x.shift(1)
    )
    metrics["spec_vs_hedge_net_chg_1w"] = metrics.groupby("market_key")["spec_vs_hedge_net"].transform(
        lambda x: x - x.shift(1)
    )
    if has_nr:
        metrics["nr_net_chg_1w"] = metrics.groupby("market_key")["nr_net"].transform(
            lambda x: x - x.shift(1)
        )
    
    # Open Interest weekly change
    # Ensure df is sorted by market_key and report_date for shift to work correctly
    df = df.sort_values(["market_key", "report_date"]).reset_index(drop=True)
    
    # Calculate previous week's open_interest within each market_key group (from canonical)
    oi_prev = df.groupby("market_key")["open_interest_all"].shift(1)
    oi_prev_numeric = pd.to_numeric(oi_prev, errors="coerce")
    oi_current_numeric = pd.to_numeric(df["open_interest_all"], errors="coerce")
    
    # Calculate absolute change: current - previous week
    # Store in df first, then copy to metrics
    df["open_interest_chg_1w"] = oi_current_numeric - oi_prev_numeric
    
    # Calculate percentage change: chg_1w / abs(prev)
    # Pure WoW % - no rolling, no normalization, no clipping
    # Edge cases: if prev is NaN or == 0 → pct = NaN
    df["open_interest_chg_1w_pct"] = np.where(
        oi_prev.notna() & (oi_prev_numeric != 0),
        df["open_interest_chg_1w"] / np.abs(oi_prev_numeric),
        np.nan
    )
    
    # Copy to metrics (ensure metrics is also sorted to match df order)
    metrics = metrics.sort_values(["market_key", "report_date"]).reset_index(drop=True)
    metrics["open_interest_chg_1w"] = df["open_interest_chg_1w"].values
    metrics["open_interest_chg_1w_pct"] = df["open_interest_chg_1w_pct"].values
    
    # Gross exposure metrics (for "Who holds the market" view)
    # funds_gross = nc_long + nc_short
    metrics["funds_gross"] = metrics["nc_long"] + metrics["nc_short"]
    
    # comm_gross = comm_long + comm_short
    metrics["comm_gross"] = metrics["comm_long"] + metrics["comm_short"]
    
    # nr_gross = nr_long + nr_short (ONLY if columns exist in canonical)
    has_nr = "nr_long" in df.columns and "nr_short" in df.columns
    if has_nr:
        metrics["nr_gross"] = pd.to_numeric(df["nr_long"], errors="coerce") + pd.to_numeric(df["nr_short"], errors="coerce")
    
    # Calculate gross_total and shares
    # gross_total = funds_gross + comm_gross + (nr_gross if present)
    if has_nr:
        gross_total = metrics["funds_gross"] + metrics["comm_gross"] + metrics["nr_gross"]
    else:
        gross_total = metrics["funds_gross"] + metrics["comm_gross"]
    
    # Shares: funds_gross_share, comm_gross_share, optional nr_gross_share
    # If gross_total == 0 or NaN → shares = NaN
    gross_total_valid = (gross_total != 0) & gross_total.notna()
    metrics["funds_gross_share"] = np.where(
        gross_total_valid,
        metrics["funds_gross"] / gross_total,
        np.nan
    )
    metrics["comm_gross_share"] = np.where(
        gross_total_valid,
        metrics["comm_gross"] / gross_total,
        np.nan
    )
    if has_nr:
        metrics["nr_gross_share"] = np.where(
            gross_total_valid,
            metrics["nr_gross"] / gross_total,
            np.nan
        )
    
    # WoW share change in percentage points (pp)
    # funds_gross_share_chg_1w_pp = (funds_gross_share - prev_share) * 100
    funds_share_prev = metrics.groupby("market_key")["funds_gross_share"].shift(1)
    metrics["funds_gross_share_chg_1w_pp"] = (metrics["funds_gross_share"] - funds_share_prev) * 100
    
    comm_share_prev = metrics.groupby("market_key")["comm_gross_share"].shift(1)
    metrics["comm_gross_share_chg_1w_pp"] = (metrics["comm_gross_share"] - comm_share_prev) * 100
    
    if has_nr:
        nr_share_prev = metrics.groupby("market_key")["nr_gross_share"].shift(1)
        metrics["nr_gross_share_chg_1w_pp"] = (metrics["nr_gross_share"] - nr_share_prev) * 100
    
    # Optional: *_gross_pct_oi (gross exposure as % of open_interest)
    # These DO NOT need to sum to 100% — that's OK
    if "open_interest" in metrics.columns:
        oi_positive = metrics["open_interest"] > 0
        metrics["funds_gross_pct_oi"] = np.where(
            oi_positive,
            metrics["funds_gross"] / metrics["open_interest"],
            np.nan
        )
        metrics["comm_gross_pct_oi"] = np.where(
            oi_positive,
            metrics["comm_gross"] / metrics["open_interest"],
            np.nan
        )
        if has_nr:
            metrics["nr_gross_pct_oi"] = np.where(
                oi_positive,
                metrics["nr_gross"] / metrics["open_interest"],
                np.nan
            )
    
    # OI v1 metrics: Change strength, participation, flows, multi-horizon
    # A) OI change strength (abs percentile, 5Y)
    metrics["open_interest_chg_1w_pct_abs"] = np.abs(metrics["open_interest_chg_1w_pct"])
    
    # Rolling 5Y min/max of abs change pct
    min_abs_5y = metrics.groupby("market_key")["open_interest_chg_1w_pct_abs"].transform(
        lambda x: x.rolling(window=260, min_periods=52).min()
    )
    max_abs_5y = metrics.groupby("market_key")["open_interest_chg_1w_pct_abs"].transform(
        lambda x: x.rolling(window=260, min_periods=52).max()
    )
    
    # Position: (curr - min) / (max - min) clipped 0..1
    diff_abs_5y = max_abs_5y - min_abs_5y
    metrics["open_interest_chg_1w_pct_abs_pos_5y"] = np.where(
        (diff_abs_5y > 0) & min_abs_5y.notna() & max_abs_5y.notna(),
        np.clip((metrics["open_interest_chg_1w_pct_abs"] - min_abs_5y) / diff_abs_5y, 0, 1),
        np.nan
    )
    
    # B) Participation / crowdedness (total as % of OI)
    # funds_total = nc_total, comm_total = comm_total, nr_total = nr_total
    if "open_interest" in metrics.columns:
        oi_positive = metrics["open_interest"] > 0
        metrics["funds_total_pct_oi"] = np.where(
            oi_positive,
            metrics["nc_total"] / metrics["open_interest"],
            np.nan
        )
        metrics["comm_total_pct_oi"] = np.where(
            oi_positive,
            metrics["comm_total"] / metrics["open_interest"],
            np.nan
        )
        if has_nr:
            metrics["nr_total_pct_oi"] = np.where(
                oi_positive,
                metrics["nr_total"] / metrics["open_interest"],
                np.nan
            )
        
        # WoW changes in percentage points
        funds_total_pct_prev = metrics.groupby("market_key")["funds_total_pct_oi"].shift(1)
        metrics["funds_total_pct_oi_chg_1w_pp"] = (metrics["funds_total_pct_oi"] - funds_total_pct_prev) * 100
        
        comm_total_pct_prev = metrics.groupby("market_key")["comm_total_pct_oi"].shift(1)
        metrics["comm_total_pct_oi_chg_1w_pp"] = (metrics["comm_total_pct_oi"] - comm_total_pct_prev) * 100
        
        if has_nr:
            nr_total_pct_prev = metrics.groupby("market_key")["nr_total_pct_oi"].shift(1)
            metrics["nr_total_pct_oi_chg_1w_pp"] = (metrics["nr_total_pct_oi"] - nr_total_pct_prev) * 100
    
    # C) Who moved (flows in %OI)
    # Use oi_prev (shift(1)) for normalization
    oi_prev = metrics.groupby("market_key")["open_interest"].shift(1)
    oi_prev_positive = (oi_prev > 0) & oi_prev.notna()
    
    # Funds flows
    metrics["funds_long_flow_pct_oi"] = np.where(
        oi_prev_positive,
        metrics["nc_long_chg_1w"] / oi_prev,
        np.nan
    )
    metrics["funds_short_flow_pct_oi"] = np.where(
        oi_prev_positive,
        metrics["nc_short_chg_1w"] / oi_prev,
        np.nan
    )
    
    # Comm flows
    metrics["comm_long_flow_pct_oi"] = np.where(
        oi_prev_positive,
        metrics["comm_long_chg_1w"] / oi_prev,
        np.nan
    )
    metrics["comm_short_flow_pct_oi"] = np.where(
        oi_prev_positive,
        metrics["comm_short_chg_1w"] / oi_prev,
        np.nan
    )
    
    # NR flows (optional)
    if has_nr:
        metrics["nr_long_flow_pct_oi"] = np.where(
            oi_prev_positive,
            metrics["nr_long_chg_1w"] / oi_prev,
            np.nan
        )
        metrics["nr_short_flow_pct_oi"] = np.where(
            oi_prev_positive,
            metrics["nr_short_chg_1w"] / oi_prev,
            np.nan
        )
    
    # D) Multi-horizon OI change (trend vs noise)
    # 4-week change
    oi_4w_prev = metrics.groupby("market_key")["open_interest"].shift(4)
    oi_4w_prev_abs = np.abs(oi_4w_prev)
    metrics["oi_chg_4w_pct"] = np.where(
        oi_4w_prev.notna() & (oi_4w_prev_abs != 0),
        (metrics["open_interest"] - oi_4w_prev) / oi_4w_prev_abs,
        np.nan
    )
    
    # 13-week change
    oi_13w_prev = metrics.groupby("market_key")["open_interest"].shift(13)
    oi_13w_prev_abs = np.abs(oi_13w_prev)
    metrics["oi_chg_13w_pct"] = np.where(
        oi_13w_prev.notna() & (oi_13w_prev_abs != 0),
        (metrics["open_interest"] - oi_13w_prev) / oi_13w_prev_abs,
        np.nan
    )
    
    # Convenience alias for 1w
    metrics["oi_chg_1w_pct"] = metrics["open_interest_chg_1w_pct"]
    
    # Also add open_interest_chg_4w_pct and open_interest_chg_13w_pct for consistency
    metrics["open_interest_chg_4w_pct"] = metrics["oi_chg_4w_pct"]
    metrics["open_interest_chg_13w_pct"] = metrics["oi_chg_13w_pct"]
    
    # Debug: log OI and flow columns
    oi_cols = [c for c in metrics.columns if 'open_interest' in c]
    flow_cols = [c for c in metrics.columns if c.endswith('_flow_pct_oi')]
    logger.info(f"[compute][debug] OI columns present: {sorted(oi_cols)}")
    logger.info(f"[compute][debug] Flow columns present: {sorted(flow_cols)}")
    
    # Rebalance decomposition metrics (nc)
    metrics["nc_gross_chg_1w"] = np.abs(metrics["nc_long_chg_1w"]) + np.abs(metrics["nc_short_chg_1w"])
    metrics["nc_net_abs_chg_1w"] = np.abs(metrics["nc_net_chg_1w"])
    metrics["nc_rebalance_chg_1w"] = metrics["nc_gross_chg_1w"] - metrics["nc_net_abs_chg_1w"]
    # rebalance_share: rebalance / gross, NaN if gross == 0
    metrics["nc_rebalance_share_1w"] = np.where(
        metrics["nc_gross_chg_1w"] > 0,
        metrics["nc_rebalance_chg_1w"] / metrics["nc_gross_chg_1w"],
        np.nan
    )
    
    # Rebalance decomposition metrics (comm)
    metrics["comm_gross_chg_1w"] = np.abs(metrics["comm_long_chg_1w"]) + np.abs(metrics["comm_short_chg_1w"])
    metrics["comm_net_abs_chg_1w"] = np.abs(metrics["comm_net_chg_1w"])
    metrics["comm_rebalance_chg_1w"] = metrics["comm_gross_chg_1w"] - metrics["comm_net_abs_chg_1w"]
    # rebalance_share: rebalance / gross, NaN if gross == 0
    metrics["comm_rebalance_share_1w"] = np.where(
        metrics["comm_gross_chg_1w"] > 0,
        metrics["comm_rebalance_chg_1w"] / metrics["comm_gross_chg_1w"],
        np.nan
    )
    
    # Rebalance decomposition metrics (nr)
    if has_nr:
        metrics["nr_gross_chg_1w"] = np.abs(metrics["nr_long_chg_1w"]) + np.abs(metrics["nr_short_chg_1w"])
        metrics["nr_net_abs_chg_1w"] = np.abs(metrics["nr_net_chg_1w"])
        metrics["nr_rebalance_chg_1w"] = metrics["nr_gross_chg_1w"] - metrics["nr_net_abs_chg_1w"]
        # rebalance_share: rebalance / gross, NaN if gross == 0
        metrics["nr_rebalance_share_1w"] = np.where(
            metrics["nr_gross_chg_1w"] > 0,
            metrics["nr_rebalance_chg_1w"] / metrics["nr_gross_chg_1w"],
            np.nan
        )
    
    # Net side indicators
    metrics["nc_net_side"] = np.where(
        metrics["nc_net"] > 0, "NET_LONG",
        np.where(metrics["nc_net"] < 0, "NET_SHORT", "FLAT")
    )
    metrics["comm_net_side"] = np.where(
        metrics["comm_net"] > 0, "NET_LONG",
        np.where(metrics["comm_net"] < 0, "NET_SHORT", "FLAT")
    )
    if has_nr:
        metrics["nr_net_side"] = np.where(
            metrics["nr_net"] > 0, "NET_LONG",
            np.where(metrics["nr_net"] < 0, "NET_SHORT", "FLAT")
        )
    
    # Net alignment
    metrics["net_alignment"] = np.where(
        (metrics["nc_net_side"] == "NET_LONG") & (metrics["comm_net_side"] == "NET_LONG"), "SAME_SIDE",
        np.where(
            (metrics["nc_net_side"] == "NET_SHORT") & (metrics["comm_net_side"] == "NET_SHORT"), "SAME_SIDE",
            np.where(
                (metrics["nc_net_side"] == "NET_LONG") & (metrics["comm_net_side"] == "NET_SHORT"), "OPPOSITE_SIDE",
                np.where(
                    (metrics["nc_net_side"] == "NET_SHORT") & (metrics["comm_net_side"] == "NET_LONG"), "OPPOSITE_SIDE",
                    "UNKNOWN"
                )
            )
        )
    )
    
    # Magnitude gap metrics
    metrics["net_mag_gap"] = np.abs(metrics["nc_net"]) - np.abs(metrics["comm_net"])
    
    # WoW change for magnitude gap
    metrics["net_mag_gap_chg_1w"] = metrics.groupby("market_key")["net_mag_gap"].transform(
        lambda x: x - x.shift(1)
    )
    
    # 5Y rolling max of abs(net_mag_gap) per market_key
    metrics["net_mag_gap_max_abs_5y"] = metrics.groupby("market_key")["net_mag_gap"].transform(
        lambda x: x.abs().rolling(window=260, min_periods=52).max()
    )
    
    # Position: abs(net_mag_gap) / net_mag_gap_max_abs_5y
    # If max_abs_5y is 0 or NaN -> NaN
    metrics["net_mag_gap_pos_5y"] = np.where(
        (metrics["net_mag_gap_max_abs_5y"] > 0) & metrics["net_mag_gap_max_abs_5y"].notna(),
        np.abs(metrics["net_mag_gap"]) / metrics["net_mag_gap_max_abs_5y"],
        np.nan
    )
    
    # Net flip flags: detect sign change between current and previous week
    # Flip = (prev != 0) AND (curr != 0) AND (sign(curr) != sign(prev))
    # If prev or curr is NaN -> flip = False
    def compute_flip(series):
        """Compute flip flag: True if sign changed from previous week, False otherwise."""
        prev = series.shift(1)
        curr = series
        
        # Sign function: 1 if >0, -1 if <0, 0 if ==0
        def sign_func(val):
            if pd.isna(val):
                return 0
            if val > 0:
                return 1
            elif val < 0:
                return -1
            else:
                return 0
        
        prev_sign = prev.apply(sign_func)
        curr_sign = curr.apply(sign_func)
        
        # Flip = (prev != 0) AND (curr != 0) AND (sign(curr) != sign(prev))
        flip = (prev_sign != 0) & (curr_sign != 0) & (curr_sign != prev_sign)
        
        # Set False for NaN cases (first row, or if prev/curr is NaN)
        flip = flip.fillna(False)
        
        return flip.astype(bool)
    
    # Compute flip flags for each net metric
    metrics["nc_net_flip_1w"] = metrics.groupby("market_key")["nc_net"].transform(compute_flip)
    metrics["comm_net_flip_1w"] = metrics.groupby("market_key")["comm_net"].transform(compute_flip)
    metrics["spec_vs_hedge_net_flip_1w"] = metrics.groupby("market_key")["spec_vs_hedge_net"].transform(compute_flip)
    if has_nr:
        metrics["nr_net_flip_1w"] = metrics.groupby("market_key")["nr_net"].transform(compute_flip)
    
    # Debug: fingerprint log
    logger.info(f"[compute][debug] build_metrics.py file={os.path.abspath(__file__)}")
    chg_cols = [c for c in metrics.columns if c.endswith("_chg_1w")]
    logger.info(f"[compute][debug] chg_1w cols present={sorted(chg_cols)}")
    
    # Assert: verify all required columns are present
    required = {
        "nc_long_chg_1w", "nc_short_chg_1w", "nc_total_chg_1w",
        "comm_long_chg_1w", "comm_short_chg_1w", "comm_total_chg_1w",
    }
    if has_nr:
        required.update({"nr_long_chg_1w", "nr_short_chg_1w", "nr_total_chg_1w"})
    missing = sorted(required - set(metrics.columns))
    if missing:
        raise RuntimeError(f"[compute] missing *_chg_1w columns: {missing}")
    
    # Assert: verify open_interest_chg_1w_pct is present before returning
    assert "open_interest_chg_1w_pct" in metrics.columns, "missing open_interest_chg_1w_pct in final metrics"
    
    return metrics
