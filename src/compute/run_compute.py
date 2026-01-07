"""CLI entrypoint for compute module."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml
import pandas as pd

from src.common.paths import ProjectPaths
from src.common.logging import setup_logging
from src.compute.build_metrics import build_metrics_weekly
from src.compute.validations import (
    validate_canonical_exists,
    validate_required_columns,
    validate_output_rows,
    validate_uniqueness,
    validate_pos_all,
    validate_pos_5y,
    validate_max_min_all,
    validate_max_min_5y,
    validate_chg_1w,
    validate_net_metrics,
    validate_oi_metrics,
    validate_exposure_shares,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    
    logger = setup_logging(args.log_level)
    
    # Debug: check sys.path to detect shadowing
    logger.info(f"[compute][debug] sys.path[0:5]={sys.path[0:5]}")
    
    paths = ProjectPaths(Path(args.root).resolve())
    
    # Read canonical_full parquet
    canonical_path = paths.canonical / "cot_weekly_canonical_full.parquet"
    validate_canonical_exists(str(canonical_path))
    
    logger.info(f"[compute] reading canonical: {canonical_path}")
    canonical = pd.read_parquet(canonical_path)
    logger.info(f"[compute] canonical rows: {len(canonical)}, cols: {len(canonical.columns)}")
    
    # Validate canonical has required columns
    required_cols = ["market_key", "report_date", "contract_code", "comm_long", "comm_short", "nc_long", "nc_short"]
    col_errors = validate_required_columns(canonical, required_cols)
    if col_errors:
        for err in col_errors:
            logger.error(f"[compute] {err}")
        raise SystemExit("Canonical missing required columns")
    
    # Read markets.yaml
    markets_path = paths.configs / "markets.yaml"
    logger.info(f"[compute] reading markets config: {markets_path}")
    cfg = yaml.safe_load(markets_path.read_text(encoding="utf-8"))
    
    # Build market mappings
    market_to_category = {}
    market_to_contract = {}
    for m in cfg["markets"]:
        market_key = m.get("market_key") or m.get("key")
        category = m.get("category")
        contract_code = m.get("contract_code")
        if market_key:
            if category:
                market_to_category[market_key] = category
            if contract_code:
                market_to_contract[market_key] = contract_code
    
    logger.info(f"[compute] loaded {len(market_to_category)} markets from config")
    
    # Build metrics
    logger.info("[compute] building metrics_weekly...")
    metrics = build_metrics_weekly(canonical, market_to_category, market_to_contract)
    
    # Validations
    errors = []
    
    # Check output rows
    errors.extend(validate_output_rows(metrics))
    
    # Check uniqueness
    errors.extend(validate_uniqueness(metrics, ["market_key", "report_date"]))
    
    # Check pos_all (no NaN, in [0, 1])
    errors.extend(validate_pos_all(metrics))
    
    # Check pos_5y (NaN allowed, non-NaN in [0, 1])
    errors.extend(validate_pos_5y(metrics))
    
    # Check max != min for ALL window
    errors.extend(validate_max_min_all(metrics))
    
    # Check max != min for 5Y window
    errors.extend(validate_max_min_5y(metrics))
    
    # Check WoW change columns (chg_1w)
    errors.extend(validate_chg_1w(metrics))
    
    # Check net metrics
    errors.extend(validate_net_metrics(metrics))
    
    # Check OI metrics
    errors.extend(validate_oi_metrics(metrics))
    
    # Check exposure shares
    errors.extend(validate_exposure_shares(metrics))
    
    if errors:
        for err in errors:
            logger.error(f"[compute] VALIDATION FAILED: {err}")
        raise SystemExit("Compute validations failed")
    
    logger.info(f"[compute] metrics rows: {len(metrics)}, cols: {len(metrics.columns)}")
    
    # List of added WoW change columns
    chg_columns = ["nc_long_chg_1w", "nc_short_chg_1w", "nc_total_chg_1w",
                   "comm_long_chg_1w", "comm_short_chg_1w", "comm_total_chg_1w"]
    logger.info(f"[compute] added columns: {', '.join(chg_columns)}")
    
    # Write output
    output_dir = paths.data / "compute"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "metrics_weekly.parquet"
    metrics.to_parquet(output_path, index=False)
    logger.info(f"[compute] wrote {output_path} rows={len(metrics)}")
    logger.info("[compute] DONE")


if __name__ == "__main__":
    main()

