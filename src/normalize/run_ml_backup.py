from __future__ import annotations

import argparse
from pathlib import Path
import logging

import pandas as pd

from src.common.paths import ProjectPaths
from src.common.logging import setup_logging
from src.ingest.manifest import load_manifest
from src.normalize.cot_parser import parse_deacot_zip


def qa_all_assets_dataset(df: pd.DataFrame) -> list[str]:
    """
    QA checks for all-assets dataset.
    
    Returns list of error messages (empty list = PASS).
    """
    errs = []
    
    # 1. Uniqueness: (contract_code, report_date) без дублів
    dup_count = df.duplicated(subset=["contract_code", "report_date"]).sum()
    if dup_count > 0:
        errs.append(f"duplicate contract_code+report_date rows: {dup_count}")
    
    # 2. contract_code len == 6
    invalid_contract_codes = df["contract_code"].astype(str).str.len() != 6
    invalid_count = invalid_contract_codes.sum()
    if invalid_count > 0:
        errs.append(f"contract_code not 6 characters: {invalid_count} rows")
    
    # 3. report_date not null
    null_dates = df["report_date"].isna().sum()
    if null_dates > 0:
        errs.append(f"null report_date detected: {null_dates} rows")
    
    # 4. open_interest_all >= 0
    negative_oi = df["open_interest_all"] < 0
    negative_count = negative_oi.sum()
    if negative_count > 0:
        errs.append(f"open_interest_all < 0: {negative_count} rows")
    
    return errs


def qa_ml_dataset(df: pd.DataFrame) -> list[str]:
    """
    QA checks for ML dataset.
    
    Returns list of error messages (empty list = PASS).
    """
    errs = []
    
    # 1. Uniqueness: (market_key, report_date) без дублів
    dup_count = df.duplicated(subset=["market_key", "report_date"]).sum()
    if dup_count > 0:
        errs.append(f"duplicate market_key+report_date rows: {dup_count}")
    
    # 2. report_date not null
    null_dates = df["report_date"].isna().sum()
    if null_dates > 0:
        errs.append(f"null report_date detected: {null_dates} rows")
    
    # 3. contract_code as string (6 characters)
    invalid_contract_codes = df["contract_code"].astype(str).str.len() != 6
    invalid_count = invalid_contract_codes.sum()
    if invalid_count > 0:
        errs.append(f"contract_code not 6 characters: {invalid_count} rows")
    
    return errs


def _select_latest_ok_snapshots(manifest_path: Path, dataset: str, root: Path, logger: logging.Logger) -> list[dict]:
    """
    Select latest OK snapshot per year from manifest.
    
    Copied logic (as per requirements: copy locally, don't import registry code).
    """
    manifest = load_manifest(manifest_path)
    
    # Filter: dataset == dataset and status == "OK"
    ok_filter = (manifest["dataset"] == dataset) & (manifest["status"] == "OK")
    ok_df = manifest[ok_filter].copy()
    
    if ok_df.empty:
        logger.warning(f"[ml_backup] No OK rows in manifest for dataset={dataset}")
        return []
    
    # Parse downloaded_at_utc for latest snapshot selection
    ok_df["_downloaded_at_utc_parsed"] = pd.to_datetime(ok_df["downloaded_at_utc"], errors="coerce", utc=True)
    
    # Group by year and select latest OK snapshot per year
    snapshots = []
    for year, group in ok_df.groupby("year"):
        if group["_downloaded_at_utc_parsed"].isna().all():
            # Fallback: last row if all timestamps are NaT
            latest_row = group.iloc[-1]
        else:
            idx = group["_downloaded_at_utc_parsed"].idxmax()
            latest_row = group.loc[idx]
        
        raw_path_str = str(latest_row["raw_path"])
        raw_path_normalized = raw_path_str.replace("\\", "/")
        raw_path_abs = root / raw_path_normalized
        
        if not raw_path_abs.exists():
            logger.warning(f"[ml_backup] year={year}: raw_path does not exist: {raw_path_abs}")
            continue
        
        snapshots.append({
            "year": int(year),
            "raw_path": raw_path_abs,
        })
    
    logger.info(f"[ml_backup] selected {len(snapshots)} snapshots for all-assets")
    return snapshots


def _build_all_assets_dataset(
    snapshots: list[dict],
    registry: pd.DataFrame,
    logger: logging.Logger
) -> pd.DataFrame:
    """
    Build all-assets dataset from raw snapshots.
    
    Reads annual.txt from ZIPs, extracts required columns, joins with registry.
    """
    all_frames = []
    
    for snapshot in snapshots:
        year = snapshot["year"]
        zp = snapshot["raw_path"]
        
        try:
            logger.info(f"[ml_backup] reading zip: {zp.name}")
            parsed = parse_deacot_zip(zp, year)
            df = parsed.df
            
            # Helper to pick column by partial name match
            def pick(col_contains: str) -> str:
                cands = [c for c in df.columns if col_contains.lower() in c.lower()]
                if not cands:
                    raise ValueError(f"Missing column contains='{col_contains}' in {zp.name}")
                return cands[0]
            
            # Report date column: priority YYYY-MM-DD, fallback YYMMDD
            if any("As of Date in Form YYYY-MM-DD" in c for c in df.columns):
                col_report_date = pick("As of Date in Form YYYY-MM-DD")
            else:
                col_report_date_candidates = [c for c in df.columns if "As of Date" in c and "YYMMDD" in c]
                if col_report_date_candidates:
                    col_report_date = col_report_date_candidates[0]
                else:
                    logger.warning(f"[ml_backup] {zp.name}: no report date column found, skipping")
                    continue
            
            # Required columns
            col_contract_code = pick("CFTC Contract Market Code")
            col_oi = pick("Open Interest (All)")
            col_comm_long = pick("Commercial Positions-Long (All)")
            col_comm_short = pick("Commercial Positions-Short (All)")
            col_nc_long = pick("Noncommercial Positions-Long (All)")
            col_nc_short = pick("Noncommercial Positions-Short (All)")
            col_nr_long = pick("Nonreportable Positions-Long (All)")
            col_nr_short = pick("Nonreportable Positions-Short (All)")
            
            # Extract and normalize
            out = pd.DataFrame({
                "contract_code": df[col_contract_code].astype(str).str.zfill(6),
                "report_date": pd.to_datetime(df[col_report_date], errors="coerce").dt.date,
                "open_interest_all": pd.to_numeric(df[col_oi], errors="coerce"),
                "comm_long": pd.to_numeric(df[col_comm_long], errors="coerce"),
                "comm_short": pd.to_numeric(df[col_comm_short], errors="coerce"),
                "noncomm_long": pd.to_numeric(df[col_nc_long], errors="coerce"),
                "noncomm_short": pd.to_numeric(df[col_nc_short], errors="coerce"),
                "nonrept_long": pd.to_numeric(df[col_nr_long], errors="coerce"),
                "nonrept_short": pd.to_numeric(df[col_nr_short], errors="coerce"),
            })
            
            # Filter out rows with invalid contract_code (not exactly 6 characters after zfill)
            out = out[out["contract_code"].str.len() == 6].copy()
            
            # Calculate net positions
            out["comm_net"] = out["comm_long"] - out["comm_short"]
            out["noncomm_net"] = out["noncomm_long"] - out["noncomm_short"]
            out["nonrept_net"] = out["nonrept_long"] - out["nonrept_short"]
            
            # Remove rows with invalid report_date
            out = out[out["report_date"].notna()].copy()
            
            if not out.empty:
                all_frames.append(out)
        
        except Exception as e:
            logger.warning(f"[ml_backup] {zp.name}: error processing: {e}")
            continue
    
    if not all_frames:
        logger.warning("[ml_backup] No data collected from snapshots")
        return pd.DataFrame()
    
    # Concatenate all data
    all_assets = pd.concat(all_frames, ignore_index=True)
    
    # Join with registry to get market_and_exchange_name and sector
    registry_cols = registry[["contract_code", "market_and_exchange_name", "sector"]].copy()
    all_assets = all_assets.merge(registry_cols, on="contract_code", how="left")
    
    # Fill sector with UNKNOWN if missing (from join)
    all_assets["sector"] = all_assets["sector"].fillna("UNKNOWN")
    
    # Sort for consistency
    all_assets = all_assets.sort_values(["contract_code", "report_date"]).reset_index(drop=True)
    
    # Select final columns in correct order
    final_columns = [
        "contract_code",
        "report_date",
        "open_interest_all",
        "comm_long",
        "comm_short",
        "comm_net",
        "noncomm_long",
        "noncomm_short",
        "noncomm_net",
        "nonrept_long",
        "nonrept_short",
        "nonrept_net",
        "market_and_exchange_name",
        "sector",
    ]
    
    all_assets = all_assets[final_columns].copy()
    
    logger.info(f"[ml_backup] built all-assets dataset: {len(all_assets)} rows")
    return all_assets


def main():
    p = argparse.ArgumentParser(description="Generate ML backup dataset from canonical")
    p.add_argument("--root", default=".", help="project root")
    p.add_argument("--log-level", default="INFO")
    p.add_argument("--csv", action="store_true", help="also write CSV file")
    p.add_argument("--all-assets", action="store_true", help="build all-assets dataset from raw snapshots")
    args = p.parse_args()

    logger = setup_logging(args.log_level)
    paths = ProjectPaths(Path(args.root).resolve())

    # All-assets mode
    if args.all_assets:
        # Read registry
        registry_path = paths.data / "registry" / "contracts_registry.parquet"
        if not registry_path.exists():
            raise FileNotFoundError(f"Registry file not found: {registry_path}. Run registry first.")
        
        logger.info(f"[ml_backup] reading registry: {registry_path}")
        registry = pd.read_parquet(registry_path)
        logger.info(f"[ml_backup] registry contracts: {len(registry)}")
        
        # Select latest OK snapshots per year
        dataset = "legacy_futures_only"
        manifest_path = paths.raw / "manifest.csv"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        
        snapshots = _select_latest_ok_snapshots(manifest_path, dataset, paths.root, logger)
        if not snapshots:
            raise SystemExit("No snapshots selected. Check manifest and raw files.")
        
        # Build all-assets dataset
        all_assets_df = _build_all_assets_dataset(snapshots, registry, logger)
        
        if all_assets_df.empty:
            raise SystemExit("All-assets dataset is empty. Check raw files.")
        
        # QA for all-assets output
        logger.info("[ml_backup] running QA checks for all-assets...")
        qa_errors = qa_all_assets_dataset(all_assets_df)
        
        if qa_errors:
            logger.error("[ml_backup] QA FAILED:\n" + "\n".join(qa_errors))
            raise SystemExit("All-assets QA failed. See errors above.")
        
        logger.info("[ml_backup] QA PASSED")
        
        # Create output directory
        ml_dir = paths.data / "ml"
        ml_dir.mkdir(parents=True, exist_ok=True)
        
        # Write parquet (required)
        parquet_path = ml_dir / "cot_weekly_all_assets.parquet"
        all_assets_df.to_parquet(parquet_path, index=False)
        logger.info(f"[ml_backup] wrote parquet: {parquet_path} (rows={len(all_assets_df)})")
        
        # Write CSV (optional)
        if args.csv:
            csv_path = ml_dir / "cot_weekly_all_assets.csv"
            all_assets_df.to_csv(csv_path, index=False)
            logger.info(f"[ml_backup] wrote CSV: {csv_path} (rows={len(all_assets_df)})")
        
        # Summary logging
        logger.info(f"[ml_backup] All-assets dataset summary:")
        logger.info(f"  rows: {len(all_assets_df)}")
        logger.info(f"  columns: {len(all_assets_df.columns)}")
        logger.info(f"  date range: {all_assets_df['report_date'].min()}..{all_assets_df['report_date'].max()}")
        logger.info(f"  unique contracts: {all_assets_df['contract_code'].nunique()}")
        logger.info("[ml_backup] DONE")
        return

    # Default behavior: ML backup from canonical (unchanged)
    canonical_path = paths.canonical / "cot_weekly_canonical.parquet"
    if not canonical_path.exists():
        raise FileNotFoundError(f"Canonical file not found: {canonical_path}")
    
    logger.info(f"[ml_backup] reading canonical: {canonical_path}")
    canonical = pd.read_parquet(canonical_path)
    logger.info(f"[ml_backup] canonical rows: {len(canonical)}, cols: {len(canonical.columns)}")

    # Select only "clean" columns for ML (Task 2.5A)
    ml_columns = [
        "market_key",
        "contract_code",
        "report_date",
        "open_interest_all",
        "comm_long",
        "comm_short",
        "comm_net",
        "noncomm_long",
        "noncomm_short",
        "noncomm_net",
        "nonrept_long",
        "nonrept_short",
        "nonrept_net",
    ]
    
    # Verify all required columns exist
    missing = [c for c in ml_columns if c not in canonical.columns]
    if missing:
        raise ValueError(f"Missing required columns in canonical: {missing}")
    
    # Extract ML dataset
    ml_df = canonical[ml_columns].copy()
    
    # Ensure contract_code is string with zfill(6)
    ml_df["contract_code"] = ml_df["contract_code"].astype(str).str.zfill(6)
    
    # Ensure report_date is date type
    ml_df["report_date"] = pd.to_datetime(ml_df["report_date"]).dt.date
    
    # Sort for consistency
    ml_df = ml_df.sort_values(["market_key", "report_date"]).reset_index(drop=True)
    
    # QA for ML output
    logger.info("[ml_backup] running QA checks...")
    qa_errors = qa_ml_dataset(ml_df)
    
    if qa_errors:
        logger.error("[ml_backup] QA FAILED:\n" + "\n".join(qa_errors))
        raise SystemExit("ML backup QA failed. See errors above.")
    
    logger.info("[ml_backup] QA PASSED")
    
    # Create output directory
    ml_dir = paths.data / "ml"
    ml_dir.mkdir(parents=True, exist_ok=True)
    
    # Write parquet (required)
    parquet_path = ml_dir / "cot_weekly_ml.parquet"
    ml_df.to_parquet(parquet_path, index=False)
    logger.info(f"[ml_backup] wrote parquet: {parquet_path} (rows={len(ml_df)})")
    
    # Write CSV (optional)
    if args.csv:
        csv_path = ml_dir / "cot_weekly_ml.csv"
        ml_df.to_csv(csv_path, index=False)
        logger.info(f"[ml_backup] wrote CSV: {csv_path} (rows={len(ml_df)})")
    
    # Summary logging
    logger.info(f"[ml_backup] ML dataset summary:")
    logger.info(f"  rows: {len(ml_df)}")
    logger.info(f"  columns: {len(ml_df.columns)}")
    logger.info(f"  date range: {ml_df['report_date'].min()}..{ml_df['report_date'].max()}")
    logger.info(f"  markets: {sorted(ml_df['market_key'].unique())}")
    logger.info("[ml_backup] DONE")


if __name__ == "__main__":
    main()

