import pandas as pd


def build_signal_status(ind: pd.DataFrame) -> pd.DataFrame:
    """
    Build MVP signal states:
      - status ∈ {ACTIVE, PAUSE} only
      - based on Funds (Non-Commercial) net flow + OI confirmation
      - deterministic: relies only on indicators row values (diff vs previous week)
    """

    required = ["market_key", "report_date", "open_interest", "funds_flow_pct_oi", "oi_chg"]
    missing = [c for c in required if c not in ind.columns]
    if missing:
        raise ValueError(f"Indicators missing required columns for signals: {missing}")

    df = ind.copy()
    df["report_date"] = pd.to_datetime(df["report_date"]).dt.date

    # --- MVP thresholds (conservative, explainable) ---
    # If you want more ACTIVE signals later, reduce min_flow_pct_oi.
    min_flow_pct_oi = 0.005   # 0.5% of OI net flow
    min_oi_chg = 0            # confirmation: OI not decreasing

    # Conditions
    missing_or_first = df["funds_flow_pct_oi"].isna() | df["open_interest"].isna() | (df["open_interest"] <= 0)
    flow_sig = df["funds_flow_pct_oi"].abs() >= min_flow_pct_oi
    oi_ok = df["oi_chg"].fillna(0) >= min_oi_chg

    status = []
    reason = []

    for i in range(len(df)):
        if bool(missing_or_first.iloc[i]):
            status.append("PAUSE")
            reason.append("NO_HISTORY_OR_BAD_OI")
            continue

        if bool(flow_sig.iloc[i]) and bool(oi_ok.iloc[i]):
            status.append("ACTIVE")
            reason.append("FLOW_OK_OI_OK")
        elif bool(flow_sig.iloc[i]) and not bool(oi_ok.iloc[i]):
            status.append("PAUSE")
            reason.append("FLOW_OK_OI_DOWN")
        else:
            status.append("PAUSE")
            reason.append("FLOW_SMALL")

    out = pd.DataFrame(
        {
            "market_key": df["market_key"].astype(str),
            "report_date": df["report_date"],
            "status": status,
            "reason_code": reason,
        }
    )

    # invariants
    allowed = {"ACTIVE", "PAUSE"}
    bad = set(out["status"].unique().tolist()) - allowed
    if bad:
        raise ValueError(f"Unexpected status values: {sorted(bad)}")

    dups = int(out.duplicated(["market_key", "report_date"]).sum())
    if dups != 0:
        raise ValueError(f"signal_status duplicates detected: {dups}")

    return out
