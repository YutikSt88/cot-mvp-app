# Project Releases

## v1.1.5 (2026-01-06)
- **removed** "Selected: ..." badge from Market page
- **cleaned** Market page UI (placeholder only)
- **updated** Documentation aligned with actual compute + UI state

## v1.1.4 (2026-01-06)
- **added** Net positioning metrics (nc_net, comm_net, spec_vs_hedge_net)
- **added** Net side & alignment tracking (nc_net_side, comm_net_side, net_alignment)
- **added** Weekly flip detection (nc_net_flip_1w, comm_net_flip_1w, spec_vs_hedge_net_flip_1w)
- **added** Magnitude gap with 5Y normalization (net_mag_gap, net_mag_gap_chg_1w, net_mag_gap_max_abs_5y, net_mag_gap_pos_5y)
- **added** New UI blocks for positioning & flow (Positioning Summary, Flow Quality)
- **restructured** UI navigation: Market as default landing page, Overview as report page with tabs (Positioning, OI, Charts), app.py as hidden technical entry point
- **added** tabbed interface in Overview: Positioning (full report), OI and Charts (placeholders)
- **hardened** Backup & rollback procedures

## v1.1.3 (2026-01-06)
- **added** WoW change metrics (*_chg_1w) for long/short/total positions
- **added** Net metrics: nc_net, comm_net, spec_vs_hedge_net + *_chg_1w
- **added** Rebalance decomposition: gross/net_abs/rebalance + share metrics
- **added** UI blocks: Asset State + Weekly Change (Δ1w) visualization

## v1.1.2 (2026-01-04)
- **removed** legacy indicators & HTML report modules
- **added** compute skeleton CLI (`src/compute/`)
- **added** full canonical parquet with COMM/NONCOMM/NONREPT long/short (`cot_weekly_canonical_full.parquet`)
- **fixed** Legacy COT mapping to ensure groups are distinct (COMM/NONCOMM/NONREPT read from different columns)

## v1.1.1 (2026-01-04)
- Release v1.1.1: ops/config sync markets from contracts_meta (enabled list)

## v1.1.0 (2026-01-04)
- Foundation upgrade: unified contract code model

## v1.0.0 (2026-01-03)
- Initial MVP release
- Ingest, Normalize, ML Backup, Registry modules




