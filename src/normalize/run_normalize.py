from __future__ import annotations

import argparse
from pathlib import Path

import yaml
import pandas as pd

from src.common.paths import ProjectPaths
from src.common.logging import setup_logging
from src.normalize.cot_parser import parse_deacot_zip
from src.normalize.qa_checks import qa_uniqueness, qa_nulls, qa_open_interest


def _normalize_market_filter(df: pd.DataFrame, cfg_market: dict) -> pd.DataFrame:
    # Legacy files typically contain "Market and Exchange Names"
    name_col_candidates = [c for c in df.columns if "Market" in c and "Name" in c]
    if not name_col_candidates:
        raise ValueError("Cannot find market name column in legacy file.")
    name_col = name_col_candidates[0]

    market_name = df[name_col].astype(str)

    # crude split into name/exchange if " - " exists
    parts = market_name.str.split(" - ", n=1, expand=True)
    mkt = parts[0].str.upper()
    ex = parts[1].fillna("").str.upper()

    any_of = [s.upper() for s in cfg_market["match"]["any_of"]]
    ex_any = [s.upper() for s in cfg_market["match"]["exchange_any_of"]]

    cond_name = False
    for s in any_of:
        cond_name = cond_name | mkt.str.contains(s, na=False)

    cond_ex = False
    for s in ex_any:
        cond_ex = cond_ex | ex.str.contains(s, na=False)

    out = df[cond_name & cond_ex].copy()
    out["_market_name"] = mkt[cond_name & cond_ex]
    out["_exchange_name"] = ex[cond_name & cond_ex]
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()

    logger = setup_logging(args.log_level)
    paths = ProjectPaths(Path(args.root).resolve())

    cfg = yaml.safe_load((paths.configs / "markets.yaml").read_text(encoding="utf-8"))
    dataset = cfg["source"]["dataset"]

    raw_dir = paths.raw / dataset
    zips = sorted(raw_dir.glob("deacot*.zip"))
    if not zips:
        raise SystemExit(f"No raw zips found in {raw_dir}")

    frames = []

    # MVP: keep only target contracts (prevents cross-rate markets creating duplicates)
    # Verified from your deacot2023.zip annual.txt output:
    # EUR: 099741 (EURO FX - CME)
    # JPY: 097741 (JAPANESE YEN - CME)
    # GBP: 096742 (BRITISH POUND - CME)
    # GOLD: 088691 (GOLD - COMEX)
    KEEP_CONTRACT_CODES = {
        "EUR": "099741",
        "JPY": "097741",
        "GBP": "096742",
        "GOLD": "088691",
    }

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

        # --- Report date column (different legacy variants) ---
        if any("As of Date in Form YYYY-MM-DD" in c for c in df.columns):
            col_report_date = pick("As of Date in Form YYYY-MM-DD")
        elif any("Report Date" in c for c in df.columns):
            col_report_date = pick("Report Date")
        else:
            # fallback (exists in your annual.txt)
            col_report_date = pick("As of Date in Form YYMMDD")

        # --- Filter to our 4 target contracts by contract market code ---
        col_contract_code = pick("CFTC Contract Market Code")
        df[col_contract_code] = df[col_contract_code].astype(str).str.zfill(6)

        allowed = set(KEEP_CONTRACT_CODES.values())
        df = df[df[col_contract_code].isin(allowed)].copy()

        # If after filter nothing left -> skip this zip (should not happen normally)
        if df.empty:
            logger.warning(f"[normalize] {zp.name}: no rows after contract-code filter")
            continue

        # Other required columns
        col_oi = pick("Open Interest")
        col_nc_long = pick("Noncommercial Positions-Long")
        col_nc_short = pick("Noncommercial Positions-Short")
        col_nc_sprd = [c for c in df.columns if "Noncommercial" in c and "Spreading" in c]
        col_nc_sprd = col_nc_sprd[0] if col_nc_sprd else None

        # Parse report_date to date
        df[col_report_date] = pd.to_datetime(df[col_report_date]).dt.date

        # Filter + map for each market in config (now df already contains only the 4 target contracts)
        for m in cfg["markets"]:
            sub = _normalize_market_filter(df, m)
            if sub.empty:
                continue

            out = pd.DataFrame({
                "market_key": m["key"],
                "market_name": sub["_market_name"].astype(str),
                "exchange_name": sub["_exchange_name"].astype(str),
                "report_date": sub[col_report_date],
                "open_interest_all": pd.to_numeric(sub[col_oi], errors="coerce"),
                "nc_long": pd.to_numeric(sub[col_nc_long], errors="coerce"),
                "nc_short": pd.to_numeric(sub[col_nc_short], errors="coerce"),
                "nc_spreading": pd.to_numeric(sub[col_nc_sprd], errors="coerce") if col_nc_sprd else 0.0,
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
