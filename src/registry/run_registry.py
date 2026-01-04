from __future__ import annotations

import argparse
from pathlib import Path

from src.common.paths import ProjectPaths
from src.common.logging import setup_logging
from src.registry.build_registry import build_registry


def main():
    p = argparse.ArgumentParser(description="Build contracts registry from raw snapshots")
    p.add_argument("--root", default=".", help="project root")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()

    logger = setup_logging(args.log_level)
    paths = ProjectPaths(Path(args.root).resolve())

    # Hardcoded dataset (same as normalize)
    dataset = "legacy_futures_only"
    manifest_path = paths.raw / "manifest.csv"
    
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    
    # Build registry
    registry = build_registry(manifest_path, dataset, paths.root, logger)
    
    if registry.empty:
        raise SystemExit("Registry is empty. Check manifest and raw files.")
    
    # Create output directory
    registry_dir = paths.data / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    
    # Write parquet (required)
    parquet_path = registry_dir / "contracts_registry.parquet"
    registry.to_parquet(parquet_path, index=False)
    logger.info(f"[registry] wrote parquet: {parquet_path} (rows={len(registry)})")
    
    # Write CSV (required, UTF-8)
    csv_path = registry_dir / "contracts_registry.csv"
    registry.to_csv(csv_path, index=False, encoding="utf-8")
    logger.info(f"[registry] wrote CSV: {csv_path} (rows={len(registry)})")
    
    # Summary logging
    logger.info(f"[registry] Registry summary:")
    logger.info(f"  contracts: {len(registry)}")
    logger.info(f"  columns: {list(registry.columns)}")
    logger.info(f"  date range: {registry['first_seen_report_date'].min()}..{registry['last_seen_report_date'].max()}")
    logger.info(f"  sector='UNKNOWN': {(registry['sector'] == 'UNKNOWN').sum()}/{len(registry)}")
    
    # Validation checks
    invalid_contract_code = registry["contract_code"].str.len() != 6
    if invalid_contract_code.any():
        logger.warning(f"[registry] WARNING: {invalid_contract_code.sum()} contract_codes with len != 6")
    else:
        logger.info(f"[registry] All contract_codes have len==6")
    
    logger.info("[registry] DONE")


if __name__ == "__main__":
    main()

