import argparse
import logging
from pathlib import Path

import pandas as pd

from src.indicators.cot_indicators import build_indicators_weekly
from src.indicators.signal_rules import build_signal_status


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    _setup_logging(args.log_level)
    log = logging.getLogger("run_indicators")

    canonical_path = Path("data/canonical/cot_weekly_canonical.parquet")
    out_dir = Path("data/indicators")
    out_dir.mkdir(parents=True, exist_ok=True)

    indicators_path = out_dir / "indicators_weekly.parquet"
    signal_path = out_dir / "signal_status.parquet"

    log.info("Reading canonical: %s", canonical_path)
    if not canonical_path.exists():
        raise FileNotFoundError(f"Canonical file not found: {canonical_path}")

    canonical = pd.read_parquet(canonical_path)
    log.info("Canonical rows=%s cols=%s", len(canonical), len(canonical.columns))

    log.info("Building indicators_weekly (Funds = Non-Commercial nc_*) ...")
    ind = build_indicators_weekly(canonical)
    log.info("Indicators rows=%s cols=%s", len(ind), len(ind.columns))

    log.info("Building signal_status (ACTIVE/PAUSE only) ...")
    sig = build_signal_status(ind)
    log.info("Signal rows=%s cols=%s", len(sig), len(sig.columns))

    # Hard gates for MVP acceptance requirements
    allowed = {"ACTIVE", "PAUSE"}
    bad = set(sig["status"].unique().tolist()) - allowed
    if bad:
        raise ValueError(f"Unexpected status values: {sorted(bad)}")

    dups = int(sig.duplicated(["market_key", "report_date"]).sum())
    if dups != 0:
        raise ValueError(f"SIG duplicates detected: {dups}")

    if len(sig) != len(ind):
        raise ValueError(f"Row mismatch: indicators={len(ind)} signal={len(sig)}")

    log.info("Writing: %s", indicators_path)
    ind.to_parquet(indicators_path, index=False)

    log.info("Writing: %s", signal_path)
    sig.to_parquet(signal_path, index=False)

    log.info("DONE ✅")


if __name__ == "__main__":
    main()
