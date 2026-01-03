from __future__ import annotations

from pathlib import Path
from typing import List, Dict

import pandas as pd

from src.ingest.manifest import load_manifest
from src.normalize.cot_parser import parse_deacot_zip


def build_registry(manifest_path: Path, dataset: str, root: Path, logger) -> pd.DataFrame:
    """
    Build contracts registry from raw snapshots.
    
    Reads manifest, selects latest OK snapshot per year,
    extracts contract information from annual.txt files,
    and aggregates by contract_code.
    """
    manifest = load_manifest(manifest_path)
    
    # Filter: dataset == "legacy_futures_only" and status == "OK"
    ok_filter = (manifest["dataset"] == dataset) & (manifest["status"] == "OK")
    ok_df = manifest[ok_filter].copy()
    
    if ok_df.empty:
        logger.warning(f"[registry] No OK rows in manifest for dataset={dataset}")
        return pd.DataFrame()
    
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
            logger.warning(f"[registry] year={year}: raw_path does not exist: {raw_path_abs}")
            continue
        
        snapshots.append({
            "year": int(year),
            "raw_path": raw_path_abs,
        })
    
    logger.info(f"[registry] selected {len(snapshots)} snapshots")
    
    # Collect all contract data
    all_contract_data = []
    total_rows_read = 0
    
    for snapshot in snapshots:
        year = snapshot["year"]
        zp = snapshot["raw_path"]
        
        try:
            logger.info(f"[registry] reading zip: {zp.name}")
            parsed = parse_deacot_zip(zp, year)
            df = parsed.df
            
            # Extract required columns
            col_contract_code = "CFTC Contract Market Code"
            col_market_exchange = "Market and Exchange Names"
            
            # Report date column: priority YYYY-MM-DD, fallback YYMMDD
            if "As of Date in Form YYYY-MM-DD" in df.columns:
                col_report_date = "As of Date in Form YYYY-MM-DD"
            else:
                # Fallback: YYMMDD (as per CR-002)
                col_report_date_candidates = [c for c in df.columns if "As of Date" in c and "YYMMDD" in c]
                if col_report_date_candidates:
                    col_report_date = col_report_date_candidates[0]
                else:
                    logger.warning(f"[registry] {zp.name}: no report date column found, skipping")
                    continue
            
            # Check required columns exist
            required_cols = [col_contract_code, col_market_exchange, col_report_date]
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                logger.warning(f"[registry] {zp.name}: missing columns {missing}, skipping")
                continue
            
            # Extract and normalize
            contract_df = pd.DataFrame({
                "contract_code": df[col_contract_code].astype(str).str.zfill(6),
                "market_and_exchange_name": df[col_market_exchange].astype(str),
                "report_date": pd.to_datetime(df[col_report_date], errors="coerce").dt.date,
            })
            
            # Validate contract_code length
            invalid_length = contract_df["contract_code"].str.len() != 6
            if invalid_length.any():
                logger.warning(f"[registry] {zp.name}: {invalid_length.sum()} rows with contract_code len != 6")
            
            # Remove rows with invalid report_date
            contract_df = contract_df[contract_df["report_date"].notna()].copy()
            
            rows_count = len(contract_df)
            total_rows_read += rows_count
            
            all_contract_data.append(contract_df)
            
        except Exception as e:
            logger.warning(f"[registry] {zp.name}: error processing: {e}")
            continue
    
    if not all_contract_data:
        logger.warning("[registry] No contract data collected")
        return pd.DataFrame()
    
    # Concatenate all data
    all_contracts = pd.concat(all_contract_data, ignore_index=True)
    
    logger.info(f"[registry] total rows read: {total_rows_read}")
    
    # Aggregate by contract_code
    logger.info(f"[registry] aggregating {len(all_contracts)} rows by contract_code")
    
    # Aggregate dates
    registry_dates = all_contracts.groupby("contract_code", as_index=False).agg({
        "report_date": ["min", "max"],
    })
    registry_dates.columns = ["contract_code", "first_seen_report_date", "last_seen_report_date"]
    
    # For market_and_exchange_name: take latest non-null (by max report_date)
    # Find index of row with max report_date per contract_code
    idx_max_date = all_contracts.groupby("contract_code")["report_date"].idxmax()
    latest_names_df = all_contracts.loc[idx_max_date, ["contract_code", "market_and_exchange_name"]].copy()
    
    # For rows where name is null, find any non-null name for that contract_code
    null_names = latest_names_df["market_and_exchange_name"].isna() | (latest_names_df["market_and_exchange_name"].astype(str).str.strip() == "")
    if null_names.any():
        # For contracts with null names at max date, find any non-null name
        for idx in latest_names_df[null_names].index:
            contract_code = latest_names_df.loc[idx, "contract_code"]
            contract_data = all_contracts[all_contracts["contract_code"] == contract_code]
            non_null_names = contract_data[
                contract_data["market_and_exchange_name"].notna() & 
                (contract_data["market_and_exchange_name"].astype(str).str.strip() != "")
            ]
            if not non_null_names.empty:
                latest_names_df.loc[idx, "market_and_exchange_name"] = non_null_names["market_and_exchange_name"].iloc[0]
    
    # Merge dates and names
    registry = registry_dates.merge(latest_names_df, on="contract_code", how="left")
    
    # Add required columns
    registry["sector"] = "UNKNOWN"
    registry["market_name"] = None
    registry["exchange_name"] = None
    
    # Ensure contract_code is string with len 6
    registry["contract_code"] = registry["contract_code"].astype(str).str.zfill(6)
    
    # Validate contract_code length
    invalid_length = registry["contract_code"].str.len() != 6
    if invalid_length.any():
        logger.warning(f"[registry] {invalid_length.sum()} contract_codes with len != 6 after aggregation")
    
    # Sort by contract_code
    registry = registry.sort_values("contract_code").reset_index(drop=True)
    
    # QA: check contract_code length
    invalid_length = registry["contract_code"].str.len() != 6
    if invalid_length.any():
        logger.warning(f"[registry] {invalid_length.sum()} contract_codes with len != 6")
    
    # QA: check date range
    invalid_dates = registry["first_seen_report_date"] > registry["last_seen_report_date"]
    if invalid_dates.any():
        logger.warning(f"[registry] {invalid_dates.sum()} contracts with first_seen > last_seen")
    
    logger.info(f"[registry] registry rows: {len(registry)}")
    if len(registry) > 0:
        logger.info(f"[registry] date range: {registry['first_seen_report_date'].min()}..{registry['last_seen_report_date'].max()}")
    
    return registry

