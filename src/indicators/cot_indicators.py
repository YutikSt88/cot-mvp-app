import pandas as pd


def build_indicators_weekly(canonical: pd.DataFrame) -> pd.DataFrame:
    """
    Input: canonical weekly table (1 row = market_key x report_date)
      - Funds (MVP) = Non-Commercial (nc_*)

    Output: indicators_weekly (1 row = market_key x report_date)
      - funds_* derived from nc_*
      - OI derived from open_interest_all
      - WoW deltas computed with groupby(diff) -> no look-ahead
      - simple quality flags for reporting/debug
    """

    required = [
        "market_key",
        "report_date",
        "open_interest_all",
        "nc_long",
        "nc_short",
        "nc_net",
    ]
    missing = [c for c in required if c not in canonical.columns]
    if missing:
        raise ValueError(f"Canonical missing required columns: {missing}")

    df = canonical.copy()

    # Ensure deterministic sorting + date type
    df["report_date"] = pd.to_datetime(df["report_date"]).dt.date
    df = df.sort_values(["market_key", "report_date"]).reset_index(drop=True)

    # Map MVP Funds = Non-Commercial
    out = pd.DataFrame(
        {
            "market_key": df["market_key"].astype(str),
            "report_date": df["report_date"],
            "market_name": df.get("market_name"),
            "exchange_name": df.get("exchange_name"),
            "open_interest": df["open_interest_all"].astype("int64", errors="ignore"),
            "funds_long": df["nc_long"].astype("int64", errors="ignore"),
            "funds_short": df["nc_short"].astype("int64", errors="ignore"),
            "funds_net": df["nc_net"].astype("int64", errors="ignore"),
            # keep lineage/debug
            "raw_source_year": df.get("raw_source_year"),
            "raw_source_file": df.get("raw_source_file"),
        }
    )

    # WoW changes (no look-ahead; uses prior week only)
    g = out.groupby("market_key", sort=False)
    out["funds_long_chg"] = g["funds_long"].diff()
    out["funds_short_chg"] = g["funds_short"].diff()
    out["funds_net_chg"] = g["funds_net"].diff()
    out["oi_chg"] = g["open_interest"].diff()

    # Normalizations (stable across markets)
    # (formulas not documented here; they are straightforward ratios)
    out["funds_net_pct_oi"] = out["funds_net"] / out["open_interest"]
    out["funds_flow_pct_oi"] = out["funds_net_chg"] / out["open_interest"]
    out["oi_chg_pct"] = out["oi_chg"] / out["open_interest"]

    # Quality flags (do NOT produce DISABLED state; signals will PAUSE on these)
    out["flag_bad_oi"] = (out["open_interest"].isna()) | (out["open_interest"] <= 0)
    out["flag_first_week"] = out["funds_net_chg"].isna()
    out["flag_flat_flow"] = out["funds_net_chg"].fillna(0).eq(0)

    # Ensure uniqueness
    dups = int(out.duplicated(["market_key", "report_date"]).sum())
    if dups != 0:
        raise ValueError(f"Indicators duplication detected: {dups}")

    return out
