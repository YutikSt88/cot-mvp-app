# CR-002: Registry + All-assets Contract Specification

## 1) Outputs

- `data/registry/contracts_registry.parquet` (required)
- `data/registry/contracts_registry.csv` (optional)
- `data/ml/cot_weekly_all_assets.parquet` (required)
- `data/ml/cot_weekly_all_assets.csv` (optional)

## 2) annual.txt columns (source-of-truth)

Source columns from CFTC annual.txt files:

- `Market and Exchange Names`
- `As of Date in Form YYYYMMDD` (fallback: `As of Date in Form YYYY-MM-DD`)
- `CFTC Contract Market Code`
- `Open Interest (All)`
- `Commercial Positions-Long (All)`
- `Commercial Positions-Short (All)`
- `Noncommercial Positions-Long (All)`
- `Noncommercial Positions-Short (All)`
- `Nonreportable Positions-Long (All)`
- `Nonreportable Positions-Short (All)`

## 3) Registry schema

`data/registry/contracts_registry.parquet` columns:

- `contract_code` (str, len=6) - CFTC Contract Market Code, zero-padded
- `market_and_exchange_name` (str) - Raw name from "Market and Exchange Names"
- `first_seen_report_date` (date) - Earliest report_date where contract appears
- `last_seen_report_date` (date) - Latest report_date where contract appears
- `sector` (str, default="UNKNOWN") - Sector classification (MVP: always UNKNOWN)
- `market_name` (nullable, optional) - Parsed market name (if available)
- `exchange_name` (nullable, optional) - Parsed exchange name (if available)

## 4) All-assets schema + QA

`data/ml/cot_weekly_all_assets.parquet` columns:

- `contract_code` (str, len=6)
- `report_date` (date)
- `open_interest_all` (numeric)
- `comm_long` (numeric)
- `comm_short` (numeric)
- `comm_net` (numeric) - calculated: comm_long - comm_short
- `noncomm_long` (numeric)
- `noncomm_short` (numeric)
- `noncomm_net` (numeric) - calculated: noncomm_long - noncomm_short
- `nonrept_long` (numeric)
- `nonrept_short` (numeric)
- `nonrept_net` (numeric) - calculated: nonrept_long - nonrept_short
- `market_and_exchange_name` (str) - from registry or annual.txt

### QA rules

- `unique (contract_code, report_date)` - no duplicates
- `contract_code len==6` - all codes must be 6 characters
- `report_date not null` - all dates must be present
- `open_interest_all >= 0` - open interest non-negative (allow 0)
- `sector == "UNKNOWN"` (MVP) - all rows must have sector="UNKNOWN" for MVP

