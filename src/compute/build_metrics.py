"""Build metrics DataFrame from canonical data."""

from __future__ import annotations

import pandas as pd


def build_metrics_weekly(
    canonical: pd.DataFrame,
    market_to_category: dict[str, str],
    market_to_contract: dict[str, str],
) -> pd.DataFrame:
    """
    Build minimal metrics DataFrame.
    
    Args:
        canonical: Canonical DataFrame with market_key, report_date
        market_to_category: Mapping from market_key to category
        market_to_contract: Mapping from market_key to contract_code
    
    Returns:
        DataFrame with columns: market_key, category, contract_code, report_date
    """
    # Filter to only markets in config
    whitelist_markets = set(market_to_category.keys())
    df = canonical[canonical["market_key"].isin(whitelist_markets)].copy()
    
    # Build metrics with required columns
    metrics = pd.DataFrame({
        "market_key": df["market_key"],
        "category": df["market_key"].map(market_to_category),
        "contract_code": df["market_key"].map(market_to_contract),
        "report_date": df["report_date"],
    })
    
    return metrics

