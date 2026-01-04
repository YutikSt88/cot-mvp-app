"""Schema definition for full canonical dataset."""

from __future__ import annotations

# Required columns for canonical_full
CANONICAL_FULL_COLUMNS = [
    # Identity
    "market_key",
    "report_date",
    "contract_code",
    # Open Interest
    "open_interest_all",
    # Commercial
    "comm_long",
    "comm_short",
    # Non-Commercial
    "nc_long",
    "nc_short",
    # Nonreportable
    "nr_long",
    "nr_short",
    # Lineage
    "raw_source_year",
    "raw_source_file",
]

# Optional columns (if present in raw, include; if not, skip)
OPTIONAL_NET_COLUMNS = [
    "comm_net",
    "nc_net",
    "nr_net",
]

