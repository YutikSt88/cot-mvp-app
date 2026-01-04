from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

# Import contract code normalization from common module
try:
    from src.common.contract_codes import normalize_contract_code
except ImportError:
    # Fallback if import fails (shouldn't happen in normal usage)
    def normalize_contract_code(x) -> str:
        s = str(x).strip().upper()
        import re
        s = re.sub(r"\.0$", "", s)
        return s


def normalize_bool(value: Any) -> bool:
    """Normalize boolean value (handles bool, str 'true'/'false', etc.)"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower().strip() in ("true", "1", "yes", "on")
    return bool(value)


def normalize_string(value: Any) -> str:
    """Normalize string: strip and uppercase"""
    return str(value).strip().upper()


def validate_contracts(contracts: list[dict]) -> list[str]:
    """
    Validate enabled contracts and return list of errors.
    
    Returns empty list if validation passes.
    """
    errors = []
    enabled_contracts = []
    
    for i, contract in enumerate(contracts):
        if not normalize_bool(contract.get("enabled", False)):
            continue
        
        enabled_contracts.append((i, contract))
    
    # Check required fields for enabled contracts
    for idx, contract in enabled_contracts:
        missing = []
        if "contract_code" not in contract or not contract["contract_code"]:
            missing.append("contract_code")
        if "symbol" not in contract or not contract["symbol"]:
            missing.append("symbol")
        if "category" not in contract or not contract["category"]:
            missing.append("category")
        
        if missing:
            errors.append(f"Contract at index {idx}: missing required fields: {', '.join(missing)}")
    
    # Check for duplicates (after normalization)
    market_keys = []
    contract_codes = []
    
    for idx, contract in enabled_contracts:
        market_key = normalize_string(contract.get("symbol", ""))
        # Use normalize_contract_code to preserve leading zeros and handle special chars
        contract_code = normalize_contract_code(contract.get("contract_code", ""))
        
        if market_key in market_keys:
            errors.append(f"Duplicate market_key: {market_key} (from contract at index {idx})")
        else:
            market_keys.append(market_key)
        
        if contract_code in contract_codes:
            errors.append(f"Duplicate contract_code: {contract_code} (from contract at index {idx})")
        else:
            contract_codes.append(contract_code)
    
    return errors


def build_markets_list(contracts: list[dict]) -> list[dict]:
    """Build markets list from enabled contracts, normalized and sorted."""
    enabled_contracts = []
    
    for contract in contracts:
        if not normalize_bool(contract.get("enabled", False)):
            continue
        
        # Use normalize_contract_code to preserve leading zeros and handle special chars
        contract_code_normalized = normalize_contract_code(contract["contract_code"])
        
        market_entry = {
            "market_key": normalize_string(contract["symbol"]),
            "contract_code": contract_code_normalized,  # Normalized but preserves leading zeros
            "category": normalize_string(contract["category"]),
        }
        enabled_contracts.append(market_entry)
    
    # Sort: first by category, then by market_key
    enabled_contracts.sort(key=lambda x: (x["category"], x["market_key"]))
    
    return enabled_contracts


def sync_markets(meta_path: Path, markets_path: Path, dry_run: bool = False) -> tuple[bool, str]:
    """
    Sync markets.yaml from contracts_meta.yaml.
    
    Returns (success: bool, message: str)
    """
    # Read contracts_meta.yaml
    if not meta_path.exists():
        return False, f"Source file not found: {meta_path}"
    
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta_data = yaml.safe_load(f)
    except Exception as e:
        return False, f"Error reading {meta_path}: {e}"
    
    if meta_data is None:
        return False, "contracts_meta.yaml is empty or invalid"
    
    # Support both formats:
    # A) Top-level list: [{...}, {...}]
    # B) Mapping with "contracts:" key: {contracts: [{...}, {...}]}
    if isinstance(meta_data, list):
        contracts = meta_data
    elif isinstance(meta_data, dict):
        contracts = meta_data.get("contracts", [])
    else:
        return False, "contracts_meta.yaml: must be a list or a mapping with 'contracts' key"
    
    if not isinstance(contracts, list):
        return False, "contracts_meta.yaml: 'contracts' must be a list"
    
    # Validate
    validation_errors = validate_contracts(contracts)
    if validation_errors:
        error_msg = "Validation failed:\n" + "\n".join(f"  - {e}" for e in validation_errors)
        return False, error_msg
    
    # Build markets list
    markets_list = build_markets_list(contracts)
    
    if not markets_list:
        return False, "No enabled contracts found in contracts_meta.yaml"
    
    # Read existing markets.yaml (if exists) to preserve other keys
    existing_data = {}
    if markets_path.exists():
        try:
            with open(markets_path, encoding="utf-8") as f:
                existing_data = yaml.safe_load(f) or {}
        except Exception as e:
            return False, f"Error reading existing {markets_path}: {e}"
    
    # Prepare output data
    output_data = existing_data.copy()
    output_data["markets"] = markets_list
    
    # Summary
    categories = sorted(set(m["category"] for m in markets_list))
    summary = f"Enabled contracts: {len(markets_list)}\n"
    summary += f"Market keys: {', '.join(sorted(m['market_key'] for m in markets_list))}\n"
    summary += f"Categories: {', '.join(categories)}"
    
    # Dry-run: show what would change
    if dry_run:
        if markets_path.exists():
            # Compare with existing
            existing_markets = existing_data.get("markets", [])
            if existing_markets != markets_list:
                return True, f"DRY-RUN: markets.yaml would be updated\n{summary}"
            else:
                return True, f"DRY-RUN: markets.yaml unchanged\n{summary}"
        else:
            return True, f"DRY-RUN: markets.yaml would be created\n{summary}"
    
    # Write markets.yaml with proper formatting
    try:
        # Custom YAML dumper that quotes contract_code values only (to preserve leading zeros)
        # We'll manually format the markets list to ensure contract_code is always quoted
        import re
        
        # Format markets list with contract_code always quoted
        formatted_markets = []
        for m in markets_list:
            formatted_markets.append({
                "market_key": m["market_key"],
                "contract_code": m["contract_code"],  # Will be quoted by dumper
                "category": m["category"],
            })
        
        output_data["markets"] = formatted_markets
        
        # Custom dumper that quotes contract_code values but not keys
        class MarketsDumper(yaml.SafeDumper):
            pass
        
        # Store original represent_str
        original_represent_str = MarketsDumper.represent_str
        
        def represent_str(dumper, data):
            # Only quote strings that look like contract codes (start with digit or contain +)
            # This avoids quoting market_key (like "EUR") and category (like "FX")
            if isinstance(data, str):
                # Contract codes typically start with digit or contain + or are all digits
                if re.match(r'^[0-9]', data) or '+' in data or re.match(r'^[0-9]+$', data):
                    if re.match(r'^[A-Z0-9+]{1,20}$', data):
                        # Quote contract codes to preserve leading zeros (e.g., "099741", "12460+")
                        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
            # For other strings, use default representation (no forced quotes)
            return original_represent_str(dumper, data)
        
        MarketsDumper.add_representer(str, represent_str)
        
        # Write with proper formatting
        with open(markets_path, "w", encoding="utf-8") as f:
            yaml.dump(
                output_data,
                f,
                Dumper=MarketsDumper,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
    except Exception as e:
        return False, f"Error writing {markets_path}: {e}"
    
    return True, f"Synced {len(markets_list)} markets to {markets_path}\n{summary}"


def main():
    parser = argparse.ArgumentParser(
        description="Sync markets.yaml from contracts_meta.yaml"
    )
    parser.add_argument(
        "--root",
        default=".",
        help="project root directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would change without writing file",
    )
    args = parser.parse_args()
    
    root = Path(args.root).resolve()
    meta_path = root / "configs" / "contracts_meta.yaml"
    markets_path = root / "configs" / "markets.yaml"
    
    success, message = sync_markets(meta_path, markets_path, dry_run=args.dry_run)
    
    print(message)
    
    if not success:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
