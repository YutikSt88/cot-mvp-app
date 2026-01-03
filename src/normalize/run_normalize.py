from __future__ import annotations

import argparse
from pathlib import Path

import yaml
import pandas as pd

from src.common.paths import ProjectPaths
from src.common.logging import setup_logging
from src.normalize.cot_parser import parse_deacot_zip
from src.normalize.qa_checks import qa_uniqueness, qa_nulls, qa_open_interest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()

    logger = setup_logging(args.log_level)
    paths = ProjectPaths(Path(args.root).resolve())

    cfg = yaml.safe_load((paths.configs / "markets.yaml").read_text(encoding="utf-8"))
    dataset = cfg["source"]["dataset"]

    # Build contract_to_market map from config
    contract_to_market = {}
    for m in cfg["markets"]:
        code = str(m.get("contract_code") or "").zfill(6)
        key = m.get("market_key") or m.get("key")
        contract_to_market[code] = key

    whitelist_codes = set(contract_to_market.keys())

    raw_dir = paths.raw / dataset
    zips = sorted(raw_dir.glob("deacot*.zip"))
    if not zips:
        raise SystemExit(f"No raw zips found in {raw_dir}")

    frames = []

    for zp in zips:
        year = int(zp.stem.replace("deacot", ""))
        parsed = parse_deacot_zip(zp, year)
        df = parsed.df

        # Detect columns for Noncommercial positions & OI (names vary slightly)
        def pick(col_contains: str) -> str:
            cands = [c for c in df.columns if col_contains.lower() in c.lower()]
            if not cands:
                raise ValueError(f"Missing column contains='{col_contains}' in {zp.name}")
            return cands[0]

        # --- Report date column ---
        if any("As of Date in Form YYYY-MM-DD" in c for c in df.columns):
            col_report_date = pick("As of Date in Form YYYY-MM-DD")
        else:
            col_report_date = pick("As of Date in Form YYYYMMDD")

        # --- Filter to whitelist contracts by contract market code ---
        col_contract_code = pick("CFTC Contract Market Code")
        df["_contract_code"] = df[col_contract_code].astype(str).str.zfill(6)

        df = df[df["_contract_code"].isin(whitelist_codes)].copy()

        if df.empty:
            logger.warning(f"[normalize] {zp.name}: no rows after contract-code filter")
            continue

        df["market_key"] = df["_contract_code"].map(contract_to_market)

        # Parse report_date to date
        df["report_date"] = pd.to_datetime(df[col_report_date], errors="coerce").dt.date

        # Build canonical DataFrame (minimal columns)
        col_oi = pick("Open Interest (All)")
        col_nc_long = pick("Noncommercial Positions-Long (All)")
        col_nc_short = pick("Noncommercial Positions-Short (All)")

        out = pd.DataFrame({
            "market_key": df["market_key"],
            "report_date": df["report_date"],
            "open_interest_all": pd.to_numeric(df[col_oi], errors="coerce"),
            "nc_long": pd.to_numeric(df[col_nc_long], errors="coerce"),
            "nc_short": pd.to_numeric(df[col_nc_short], errors="coerce"),
            "raw_source_year": year,
            "raw_source_file": parsed.source_file,
        })
        out["nc_net"] = out["nc_long"] - out["nc_short"]
        frames.append(out)

    if not frames:
        raise SystemExit("No rows produced during normalization (frames empty). Check raw files & filters.")

    canonical = pd.concat(frames, ignore_index=True)
    canonical = canonical.sort_values(["market_key", "report_date"]).reset_index(drop=True)

    # QA
    errors = []
    errors += qa_uniqueness(canonical)
    errors += qa_nulls(canonical, max_null_ratio=0.001)
    errors += qa_open_interest(canonical)

    qa_path = paths.canonical / "qa_report.txt"
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text("\n".join(errors) if errors else "OK", encoding="utf-8")

    if errors:
        logger.error("[normalize] QA FAILED:\n" + "\n".join(errors))
        raise SystemExit("Normalization QA failed. See data/canonical/qa_report.txt")

    out_path = paths.canonical / "cot_weekly_canonical.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canonical.to_parquet(out_path, index=False)
    logger.info(f"[normalize] wrote {out_path} rows={len(canonical)}")


if __name__ == "__main__":
    main()
