# NR Coverage Audit Report

**Date:** 2026-01-07  
**Scope:** Nonreportable (NR) data presence vs. compute/validations/UI coverage  
**Status:** Read-only audit (no code changes)

---

## 1) Data Schema Reality

### Canonical Participant Columns

**Source:** `src/normalize/canonical_full_schema.py`

**NC (Non-Commercial / Funds):**
- `nc_long` (required)
- `nc_short` (required)
- `nc_net` (optional, computed if present)

**COMM (Commercial):**
- `comm_long` (required)
- `comm_short` (required)
- `comm_net` (optional, computed if present)

**NR (Nonreportable):**
- `nr_long` (required) ✅ **PRESENT**
- `nr_short` (required) ✅ **PRESENT**
- `nr_net` (optional, computed if present) ✅ **PRESENT**

**Conclusion:** NR columns exist in canonical schema and are expected in `cot_weekly_canonical_full.parquet`.

---

### Metrics Output Columns

**Source:** `src/compute/build_metrics.py` (lines 49-383)

**NC metrics computed:**
- Base: `nc_long`, `nc_short`, `nc_total`
- Net: `nc_net`
- Heat-range (ALL): `nc_{long,short,total}_{min,max,pos}_all` (6 columns)
- Heat-range (5Y): `nc_{long,short,total}_{min,max,pos}_5y` (6 columns)
- WoW changes: `nc_{long,short,total}_chg_1w` (3 columns)
- Net change: `nc_net_chg_1w`
- Rebalance: `nc_gross_chg_1w`, `nc_net_abs_chg_1w`, `nc_rebalance_chg_1w`, `nc_rebalance_share_1w` (4 columns)
- Net side: `nc_net_side`
- Flip: `nc_net_flip_1w`
- Gross exposure: `funds_gross` (alias for `nc_long + nc_short`)
- Gross shares: `funds_gross_share`, `funds_gross_share_chg_1w_pp`, `funds_gross_pct_oi` (3 columns)

**COMM metrics computed:**
- Base: `comm_long`, `comm_short`, `comm_total`
- Net: `comm_net`
- Heat-range (ALL): `comm_{long,short,total}_{min,max,pos}_all` (6 columns)
- Heat-range (5Y): `comm_{long,short,total}_{min,max,pos}_5y` (6 columns)
- WoW changes: `comm_{long,short,total}_chg_1w` (3 columns)
- Net change: `comm_net_chg_1w`
- Rebalance: `comm_gross_chg_1w`, `comm_net_abs_chg_1w`, `comm_rebalance_chg_1w`, `comm_rebalance_share_1w` (4 columns)
- Net side: `comm_net_side`
- Flip: `comm_net_flip_1w`
- Gross exposure: `comm_gross` (alias for `comm_long + comm_short`)
- Gross shares: `comm_gross_share`, `comm_gross_share_chg_1w_pp`, `comm_gross_pct_oi` (3 columns)

**NR metrics computed:**
- Base: ❌ **MISSING** — no `nr_long`, `nr_short`, `nr_total` in metrics
- Net: ❌ **MISSING** — no `nr_net`
- Heat-range (ALL): ❌ **MISSING** — no `nr_{long,short,total}_{min,max,pos}_all` (6 columns)
- Heat-range (5Y): ❌ **MISSING** — no `nr_{long,short,total}_{min,max,pos}_5y` (6 columns)
- WoW changes: ❌ **MISSING** — no `nr_{long,short,total}_chg_1w` (3 columns)
- Net change: ❌ **MISSING** — no `nr_net_chg_1w`
- Rebalance: ❌ **MISSING** — no `nr_gross_chg_1w`, `nr_net_abs_chg_1w`, `nr_rebalance_chg_1w`, `nr_rebalance_share_1w` (4 columns)
- Net side: ❌ **MISSING** — no `nr_net_side`
- Flip: ❌ **MISSING** — no `nr_net_flip_1w`
- Gross exposure: ✅ **PARTIAL** — `nr_gross` exists (lines 197-200), but only if `nr_long`/`nr_short` exist in canonical
- Gross shares: ✅ **PARTIAL** — `nr_gross_share`, `nr_gross_share_chg_1w_pp`, `nr_gross_pct_oi` exist (lines 222-260), but only if NR exists

**Summary:** NR has **only 4 metrics** (gross + shares) vs. **~40 metrics** for NC/COMM.

---

## 2) Compute Layer: Where NR is Missing

### Missing Area 1: Base Position Metrics

**File:** `src/compute/build_metrics.py`  
**Function/Block:** `build_metrics_weekly()` lines 49-56  
**NC/COMM metrics currently computed:**
```python
metrics["nc_long"] = pd.to_numeric(df["nc_long"], errors="coerce")
metrics["nc_short"] = pd.to_numeric(df["nc_short"], errors="coerce")
metrics["nc_total"] = metrics["nc_long"] + metrics["nc_short"]
metrics["comm_long"] = pd.to_numeric(df["comm_long"], errors="coerce")
metrics["comm_short"] = pd.to_numeric(df["comm_short"], errors="coerce")
metrics["comm_total"] = metrics["comm_long"] + metrics["comm_short"]
```

**NR equivalent missing:**
- `nr_long`, `nr_short`, `nr_total` not computed

**Proposed fix:**
```python
# After line 56, add:
has_nr = "nr_long" in df.columns and "nr_short" in df.columns
if has_nr:
    metrics["nr_long"] = pd.to_numeric(df["nr_long"], errors="coerce")
    metrics["nr_short"] = pd.to_numeric(df["nr_short"], errors="coerce")
    metrics["nr_total"] = metrics["nr_long"] + metrics["nr_short"]
```

**Risk level:** Low (additive, no breaking changes)

---

### Missing Area 2: Net Exposure Metrics

**File:** `src/compute/build_metrics.py`  
**Function/Block:** `build_metrics_weekly()` lines 58-61  
**NC/COMM metrics currently computed:**
```python
metrics["nc_net"] = metrics["nc_long"] - metrics["nc_short"]
metrics["comm_net"] = metrics["comm_long"] - metrics["comm_short"]
metrics["spec_vs_hedge_net"] = metrics["nc_net"] - metrics["comm_net"]
```

**NR equivalent missing:**
- `nr_net` not computed
- `spec_vs_hedge_net` assumes only 2 groups (NC vs COMM)

**Proposed fix:**
```python
# After line 61, add:
if has_nr:
    metrics["nr_net"] = metrics["nr_long"] - metrics["nr_short"]
# Note: spec_vs_hedge_net remains NC - COMM (by design, NR not included in spec vs hedge)
```

**Risk level:** Low (additive)

---

### Missing Area 3: Heat-Range Metrics (ALL Window)

**File:** `src/compute/build_metrics.py`  
**Function/Block:** `build_metrics_weekly()` lines 72-88  
**NC/COMM metrics currently computed:**
- Loop over `groups = ["nc", "comm"]` and `sides = ["long", "short", "total"]`
- Computes: `{group}_{side}_{min,max,pos}_all` (6 columns per group = 12 total)

**NR equivalent missing:**
- `nr_{long,short,total}_{min,max,pos}_all` (6 columns)

**Proposed fix:**
```python
# Line 69: Change groups list
groups = ["nc", "comm"]
# To:
groups = ["nc", "comm"]
if has_nr:
    groups.append("nr")
# The existing loop (lines 73-88) will automatically compute NR metrics
```

**Risk level:** Low (loop-based, no code duplication)

---

### Missing Area 4: Heat-Range Metrics (5Y Rolling Window)

**File:** `src/compute/build_metrics.py`  
**Function/Block:** `build_metrics_weekly()` lines 90-116  
**NC/COMM metrics currently computed:**
- Same loop structure as ALL window
- Computes: `{group}_{side}_{min,max,pos}_5y` (6 columns per group = 12 total)

**NR equivalent missing:**
- `nr_{long,short,total}_{min,max,pos}_5y` (6 columns)

**Proposed fix:**
- Same as Missing Area 3 (extend `groups` list)

**Risk level:** Low

---

### Missing Area 5: WoW Change Metrics (Base Positions)

**File:** `src/compute/build_metrics.py`  
**Function/Block:** `build_metrics_weekly()` lines 141-150  
**NC/COMM metrics currently computed:**
- Loop over `groups = ["nc", "comm"]` and `sides = ["long", "short", "total"]`
- Computes: `{group}_{side}_chg_1w` (3 columns per group = 6 total)

**NR equivalent missing:**
- `nr_{long,short,total}_chg_1w` (3 columns)

**Proposed fix:**
- Same as Missing Area 3 (extend `groups` list)

**Risk level:** Low

---

### Missing Area 6: Net Change Metrics

**File:** `src/compute/build_metrics.py`  
**Function/Block:** `build_metrics_weekly()` lines 152-161  
**NC/COMM metrics currently computed:**
```python
metrics["nc_net_chg_1w"] = metrics.groupby("market_key")["nc_net"].transform(lambda x: x - x.shift(1))
metrics["comm_net_chg_1w"] = metrics.groupby("market_key")["comm_net"].transform(lambda x: x - x.shift(1))
metrics["spec_vs_hedge_net_chg_1w"] = metrics.groupby("market_key")["spec_vs_hedge_net"].transform(lambda x: x - x.shift(1))
```

**NR equivalent missing:**
- `nr_net_chg_1w` not computed

**Proposed fix:**
```python
# After line 161, add:
if has_nr:
    metrics["nr_net_chg_1w"] = metrics.groupby("market_key")["nr_net"].transform(lambda x: x - x.shift(1))
```

**Risk level:** Low

---

### Missing Area 7: Rebalance Decomposition Metrics

**File:** `src/compute/build_metrics.py`  
**Function/Block:** `build_metrics_weekly()` lines 262-282  
**NC/COMM metrics currently computed:**
```python
# NC rebalance (lines 262-271)
metrics["nc_gross_chg_1w"] = np.abs(metrics["nc_long_chg_1w"]) + np.abs(metrics["nc_short_chg_1w"])
metrics["nc_net_abs_chg_1w"] = np.abs(metrics["nc_net_chg_1w"])
metrics["nc_rebalance_chg_1w"] = metrics["nc_gross_chg_1w"] - metrics["nc_net_abs_chg_1w"]
metrics["nc_rebalance_share_1w"] = np.where(...)

# COMM rebalance (lines 273-282)
metrics["comm_gross_chg_1w"] = np.abs(metrics["comm_long_chg_1w"]) + np.abs(metrics["comm_short_chg_1w"])
metrics["comm_net_abs_chg_1w"] = np.abs(metrics["comm_net_chg_1w"])
metrics["comm_rebalance_chg_1w"] = metrics["comm_gross_chg_1w"] - metrics["comm_net_abs_chg_1w"]
metrics["comm_rebalance_share_1w"] = np.where(...)
```

**NR equivalent missing:**
- `nr_gross_chg_1w`, `nr_net_abs_chg_1w`, `nr_rebalance_chg_1w`, `nr_rebalance_share_1w` (4 columns)

**Proposed fix:**
```python
# After line 282, add:
if has_nr:
    metrics["nr_gross_chg_1w"] = np.abs(metrics["nr_long_chg_1w"]) + np.abs(metrics["nr_short_chg_1w"])
    metrics["nr_net_abs_chg_1w"] = np.abs(metrics["nr_net_chg_1w"])
    metrics["nr_rebalance_chg_1w"] = metrics["nr_gross_chg_1w"] - metrics["nr_net_abs_chg_1w"]
    metrics["nr_rebalance_share_1w"] = np.where(
        metrics["nr_gross_chg_1w"] > 0,
        metrics["nr_rebalance_chg_1w"] / metrics["nr_gross_chg_1w"],
        np.nan
    )
```

**Risk level:** Medium (depends on Missing Area 5 being fixed first)

---

### Missing Area 8: Net Side Indicators

**File:** `src/compute/build_metrics.py`  
**Function/Block:** `build_metrics_weekly()` lines 284-292  
**NC/COMM metrics currently computed:**
```python
metrics["nc_net_side"] = np.where(metrics["nc_net"] > 0, "NET_LONG", np.where(metrics["nc_net"] < 0, "NET_SHORT", "FLAT"))
metrics["comm_net_side"] = np.where(metrics["comm_net"] > 0, "NET_LONG", np.where(metrics["comm_net"] < 0, "NET_SHORT", "FLAT"))
```

**NR equivalent missing:**
- `nr_net_side` not computed

**Proposed fix:**
```python
# After line 292, add:
if has_nr:
    metrics["nr_net_side"] = np.where(metrics["nr_net"] > 0, "NET_LONG", np.where(metrics["nr_net"] < 0, "NET_SHORT", "FLAT"))
```

**Risk level:** Low

---

### Missing Area 9: Net Alignment Logic

**File:** `src/compute/build_metrics.py`  
**Function/Block:** `build_metrics_weekly()` lines 294-307  
**NC/COMM metrics currently computed:**
- `net_alignment` compares only NC vs COMM (SAME_SIDE, OPPOSITE_SIDE, UNKNOWN)

**NR equivalent missing:**
- No NR-inclusive alignment metric (e.g., 3-way alignment)

**Proposed fix:**
- **Design decision needed:** Should we add `nr_alignment_vs_nc`, `nr_alignment_vs_comm`, or a 3-way alignment?
- **Recommendation:** Add optional `nr_alignment_vs_nc` and `nr_alignment_vs_comm` (similar to existing `net_alignment`)

**Risk level:** Medium (requires design decision)

---

### Missing Area 10: Net Flip Flags

**File:** `src/compute/build_metrics.py`  
**Function/Block:** `build_metrics_weekly()` lines 330-363  
**NC/COMM metrics currently computed:**
```python
metrics["nc_net_flip_1w"] = metrics.groupby("market_key")["nc_net"].transform(compute_flip)
metrics["comm_net_flip_1w"] = metrics.groupby("market_key")["comm_net"].transform(compute_flip)
metrics["spec_vs_hedge_net_flip_1w"] = metrics.groupby("market_key")["spec_vs_hedge_net"].transform(compute_flip)
```

**NR equivalent missing:**
- `nr_net_flip_1w` not computed

**Proposed fix:**
```python
# After line 363, add:
if has_nr:
    metrics["nr_net_flip_1w"] = metrics.groupby("market_key")["nr_net"].transform(compute_flip)
```

**Risk level:** Low

---

### Missing Area 11: Assertion for Required Columns

**File:** `src/compute/build_metrics.py`  
**Function/Block:** `build_metrics_weekly()` lines 370-377  
**NC/COMM metrics currently computed:**
- Assert checks for 6 required `*_chg_1w` columns (nc + comm only)

**NR equivalent missing:**
- Assert does not check for NR `*_chg_1w` columns

**Proposed fix:**
```python
# Line 371-374: Update required set
required = {
    "nc_long_chg_1w", "nc_short_chg_1w", "nc_total_chg_1w",
    "comm_long_chg_1w", "comm_short_chg_1w", "comm_total_chg_1w",
}
# Add conditional:
if has_nr:
    required.update({"nr_long_chg_1w", "nr_short_chg_1w", "nr_total_chg_1w"})
```

**Risk level:** Low

---

## 3) Validations: Where NR is Missing

### Validation 1: Position Heat-Range (ALL Window)

**File:** `src/compute/validations.py`  
**Function:** `validate_pos_all()` lines 50-83  
**NC/COMM validations:**
- Loops over `groups = ["nc", "comm"]` and `sides = ["long", "short", "total"]`
- Validates: no NaN, all values in [0, 1]

**NR analogs missing:**
- No validation for `nr_{long,short,total}_pos_all`

**Proposed fix:**
```python
# Line 61: Extend groups list
groups = ["nc", "comm"]
# To:
groups = ["nc", "comm"]
# Check if NR exists in df
has_nr = any("nr_" in col and "_pos_all" in col for col in df.columns)
if has_nr:
    groups.append("nr")
```

**Risk level:** Low

---

### Validation 2: Position Heat-Range (5Y Window)

**File:** `src/compute/validations.py`  
**Function:** `validate_pos_5y()` lines 86-114  
**NC/COMM validations:**
- Same loop structure as `validate_pos_all()`
- Validates: NaN allowed, non-NaN in [0, 1]

**NR analogs missing:**
- No validation for `nr_{long,short,total}_pos_5y`

**Proposed fix:**
- Same as Validation 1 (extend `groups` list)

**Risk level:** Low

---

### Validation 3: Max/Min ALL Window

**File:** `src/compute/validations.py`  
**Function:** `validate_max_min_all()` lines 117-144  
**NC/COMM validations:**
- Loops over `groups = ["nc", "comm"]` and `sides = ["long", "short", "total"]`
- Validates: max != min (must be 0 rows where max==min)

**NR analogs missing:**
- No validation for `nr_{long,short,total}_{min,max}_all`

**Proposed fix:**
- Same as Validation 1 (extend `groups` list)

**Risk level:** Low

---

### Validation 4: Max/Min 5Y Window

**File:** `src/compute/validations.py`  
**Function:** `validate_max_min_5y()` lines 147-175  
**NC/COMM validations:**
- Same loop structure as `validate_max_min_all()`
- Validates: max != min (only NaN from min_periods allowed)

**NR analogs missing:**
- No validation for `nr_{long,short,total}_{min,max}_5y`

**Proposed fix:**
- Same as Validation 1 (extend `groups` list)

**Risk level:** Low

---

### Validation 5: WoW Change Columns

**File:** `src/compute/validations.py`  
**Function:** `validate_chg_1w()` lines 178-270  
**NC/COMM validations:**
- Loops over `groups = ["nc", "comm"]` and `sides = ["long", "short", "total"]`
- Validates: NaN only for first row, no inf, formula check

**NR analogs missing:**
- No validation for `nr_{long,short,total}_chg_1w`

**Proposed fix:**
- Same as Validation 1 (extend `groups` list)

**Risk level:** Low

---

### Validation 6: Net Metrics

**File:** `src/compute/validations.py`  
**Function:** `validate_net_metrics()` lines 273-395  
**NC/COMM validations:**
- Validates: `nc_net`, `comm_net`, `nc_net_chg_1w`, `comm_net_chg_1w`, `spec_vs_hedge_net`, `spec_vs_hedge_net_chg_1w`
- Formula checks: `nc_net == nc_long - nc_short`, `comm_net == comm_long - comm_short`
- No NaN in net columns, NaN only for first row in `*_chg_1w`

**NR analogs missing:**
- No validation for `nr_net`, `nr_net_chg_1w`
- No formula check: `nr_net == nr_long - nr_short`

**Proposed fix:**
```python
# Line 292-296: Extend required_cols
required_cols = [
    "nc_net", "comm_net",
    "nc_net_chg_1w", "comm_net_chg_1w",
    "spec_vs_hedge_net", "spec_vs_hedge_net_chg_1w"
]
# Add conditional:
has_nr = "nr_net" in df.columns
if has_nr:
    required_cols.extend(["nr_net", "nr_net_chg_1w"])

# After line 332: Add formula check
if has_nr and "nr_long" in df_sorted.columns and "nr_short" in df_sorted.columns:
    expected_nr_net = df_sorted["nr_long"] - df_sorted["nr_short"]
    diff_nr_net = np.abs(df_sorted["nr_net"] - expected_nr_net)
    max_diff = diff_nr_net.max()
    if max_diff > 1e-6:
        errors.append(f"nr_net formula mismatch: max diff = {max_diff:.2e}")

# Line 345: Add to NaN check loop
for col in ["nc_net", "comm_net", "spec_vs_hedge_net"]:
    # Add:
    if has_nr:
        # Check nr_net separately
```

**Risk level:** Medium (requires careful integration)

---

### Validation 7: Rebalance Metrics

**File:** `src/compute/validations.py`  
**Function:** `validate_rebalance_metrics()` lines 621-769  
**NC/COMM validations:**
- Loops over `prefix in ["nc", "comm"]`
- Validates: 8 columns per group (gross_chg, net_abs_chg, rebalance_chg, rebalance_share)
- Formula checks, bounds checks

**NR analogs missing:**
- No validation for `nr_gross_chg_1w`, `nr_net_abs_chg_1w`, `nr_rebalance_chg_1w`, `nr_rebalance_share_1w`

**Proposed fix:**
```python
# Line 637-640: Extend required_cols conditionally
required_cols = [
    "nc_gross_chg_1w", "nc_net_abs_chg_1w", "nc_rebalance_chg_1w", "nc_rebalance_share_1w",
    "comm_gross_chg_1w", "comm_net_abs_chg_1w", "comm_rebalance_chg_1w", "comm_rebalance_share_1w"
]
has_nr = all(col in df.columns for col in ["nr_gross_chg_1w", "nr_net_abs_chg_1w", "nr_rebalance_chg_1w", "nr_rebalance_share_1w"])
if has_nr:
    required_cols.extend(["nr_gross_chg_1w", "nr_net_abs_chg_1w", "nr_rebalance_chg_1w", "nr_rebalance_share_1w"])

# Line 697: Extend loop
for prefix in ["nc", "comm"]:
    # Add:
    if has_nr:
        # Process "nr" prefix similarly
```

**Risk level:** Medium (requires loop extension)

---

### Validation 8: Net Side and Magnitude Gap

**File:** `src/compute/validations.py`  
**Function:** `validate_net_side_and_mag_gap()` lines 398-505  
**NC/COMM validations:**
- Validates: `nc_net_side`, `comm_net_side`, `net_alignment`, `net_mag_gap`, `net_mag_gap_chg_1w`, `net_mag_gap_max_abs_5y`, `net_mag_gap_pos_5y`
- Formula checks, value checks

**NR analogs missing:**
- No validation for `nr_net_side`
- `net_alignment` assumes only 2 groups (NC vs COMM)

**Proposed fix:**
```python
# Line 416-420: Extend required_cols conditionally
required_cols = [
    "nc_net_side", "comm_net_side", "net_alignment",
    "net_mag_gap", "net_mag_gap_chg_1w",
    "net_mag_gap_max_abs_5y", "net_mag_gap_pos_5y"
]
has_nr = "nr_net_side" in df.columns
if has_nr:
    required_cols.append("nr_net_side")

# Line 483-491: Add NR net_side validation
if has_nr:
    valid_sides = {"NET_LONG", "NET_SHORT", "FLAT"}
    invalid = set(df_sorted["nr_net_side"].unique()) - valid_sides
    if invalid:
        errors.append(f"nr_net_side: invalid values found: {sorted(invalid)}")
```

**Risk level:** Low

---

### Validation 9: Net Flip Flags

**File:** `src/compute/validations.py`  
**Function:** `validate_net_flip_flags()` lines 508-618  
**NC/COMM validations:**
- Validates: `nc_net_flip_1w`, `comm_net_flip_1w`, `spec_vs_hedge_net_flip_1w`
- Type checks, formula checks

**NR analogs missing:**
- No validation for `nr_net_flip_1w`

**Proposed fix:**
```python
# Line 522-526: Extend required_cols conditionally
required_cols = [
    "nc_net_flip_1w",
    "comm_net_flip_1w",
    "spec_vs_hedge_net_flip_1w"
]
has_nr = "nr_net_flip_1w" in df.columns
if has_nr:
    required_cols.append("nr_net_flip_1w")

# After line 616: Add NR flip validation
if has_nr and "nr_net" in df_sorted.columns:
    prev_nr = df_sorted.groupby("market_key")["nr_net"].shift(1)
    curr_nr = df_sorted["nr_net"]
    # ... (same logic as NC/COMM)
```

**Risk level:** Low

---

### Validation 10: Exposure Shares

**File:** `src/compute/validations.py`  
**Function:** `validate_exposure_shares()` lines 879-1027  
**NC/COMM validations:**
- Validates: `funds_gross`, `comm_gross`, `funds_gross_share`, `comm_gross_share`, `funds_gross_share_chg_1w_pp`, `comm_gross_share_chg_1w_pp`
- Conditional: NR columns if `nr_long`/`nr_short` exist

**NR analogs:**
- ✅ **PARTIALLY COVERED** — NR validations exist (lines 913-1025), but only if NR columns are detected

**Conclusion:** This validation is **already NR-aware** and correctly handles conditional NR presence.

---

## 4) UI: Where NR is Missing by Design vs Accidentally

### UI Block 1: Asset State (Positioning Tab)

**File:** `src/app/pages/overview.py`  
**Location:** Lines 213-229 (NC column), 231-247 (COMM column)  
**Current behavior:**
- Two columns: NC (left) and COMM (right)
- Shows: ALL Time and Last 5 Years heatline bars for long/short/total

**NR status:**
- ❌ **MISSING** — No third column for NR

**Design decision:**
- **Intentional:** UI shows only NC and COMM (by design, NR is "small traders" and less relevant for positioning analysis)
- **OR Accidental:** Could add third column if NR metrics exist

**Recommendation:** Keep as-is (by design), but document that NR is intentionally excluded from positioning view.

**Risk level:** N/A (design decision)

---

### UI Block 2: Weekly Change (Positioning Tab)

**File:** `src/app/pages/overview.py`  
**Location:** Lines 385-397  
**Current behavior:**
- Two columns: NC (left) and COMM (right)
- Shows: WoW change bars for long/short

**NR status:**
- ❌ **MISSING** — No third column for NR

**Design decision:**
- Same as UI Block 1

**Risk level:** N/A (design decision)

---

### UI Block 3: Positioning Summary (Net Sides / Divergence / Magnitude)

**File:** `src/app/pages/overview.py`  
**Location:** Lines 399-637  
**Current behavior:**
- Shows: NC net side, COMM net side, alignment, magnitude gap
- Visual: Range line with 2 markers (NC and COMM)

**NR status:**
- ❌ **MISSING** — No NR net side or alignment
- ⚠️ **BREAKS IF NR ADDED:** Range line assumes 2 groups (would need 3rd marker)

**Design decision:**
- **Accidental:** Logic assumes only 2 groups (NC vs COMM)
- If NR added, would need: 3-way alignment logic, 3rd marker on range line

**Recommendation:** Document that this block assumes 2 groups. If NR is added, refactor to support 3 groups.

**Risk level:** High (would break if NR metrics added without UI refactor)

---

### UI Block 4: Data Table (Positioning Tab)

**File:** `src/app/pages/overview.py`  
**Location:** Lines 900-943  
**Current behavior:**
- Shows last 20 weeks of data
- Columns: `nc_*`, `comm_*`, `net_*`, `open_interest_*`

**NR status:**
- ❌ **MISSING** — No `nr_*` columns displayed

**Design decision:**
- **Accidental:** Table shows whatever columns exist in metrics
- If NR metrics are added, they would automatically appear (unless filtered out)

**Recommendation:** Add `nr_*` columns to display list if they exist.

**Risk level:** Low (additive)

---

### UI Block 5: OI Tab - Exposure Shares

**File:** `src/app/pages/overview.py`  
**Location:** Lines 1068-1189  
**Current behavior:**
- Shows: Stacked 100% bar with Funds, Commercial, and optional Nonreportable
- Shows: WoW pp changes for all three groups

**NR status:**
- ✅ **COVERED** — NR is already included (lines 1082-1179)
- Conditional: Only shows if `nr_gross_share` exists

**Conclusion:** This block is **already NR-aware** and correctly handles conditional NR presence.

**Risk level:** N/A (already implemented)

---

## 5) Priority Patch Plan (Next Steps)

### Patch 1: Compute Symmetry - Base Position Metrics (HIGH PRIORITY)

**Files to edit:**
- `src/compute/build_metrics.py`

**Columns to add:**
- `nr_long`, `nr_short`, `nr_total`
- `nr_net`

**Changes:**
1. After line 56, add conditional NR base metrics
2. After line 61, add conditional `nr_net`

**Acceptance criteria:**
- `nr_long`, `nr_short`, `nr_total`, `nr_net` exist in `metrics_weekly.parquet` when NR data is present
- Formulas: `nr_total == nr_long + nr_short`, `nr_net == nr_long - nr_short`
- No breaking changes to existing NC/COMM metrics

**Risk level:** Low

---

### Patch 2: Compute Symmetry - Heat-Range Metrics (HIGH PRIORITY)

**Files to edit:**
- `src/compute/build_metrics.py`

**Columns to add:**
- `nr_{long,short,total}_{min,max,pos}_all` (6 columns)
- `nr_{long,short,total}_{min,max,pos}_5y` (6 columns)

**Changes:**
1. Line 69: Extend `groups` list conditionally to include `"nr"`
2. Existing loops (lines 73-88, 92-116) will automatically compute NR metrics

**Acceptance criteria:**
- All 12 NR heat-range columns exist when NR data is present
- `nr_*_pos_all` has no NaN (same as NC/COMM)
- `nr_*_pos_5y` has NaN only at start (min_periods=52)

**Risk level:** Low

---

### Patch 3: Compute Symmetry - WoW Change Metrics (HIGH PRIORITY)

**Files to edit:**
- `src/compute/build_metrics.py`

**Columns to add:**
- `nr_{long,short,total}_chg_1w` (3 columns)
- `nr_net_chg_1w` (1 column)

**Changes:**
1. Line 143: Extend `groups` list conditionally (same as Patch 2)
2. After line 161, add conditional `nr_net_chg_1w`

**Acceptance criteria:**
- All 4 NR change columns exist when NR data is present
- NaN only for first row per market_key
- Formula: `nr_*_chg_1w == current - shift(1)`

**Risk level:** Low

---

### Patch 4: Compute Symmetry - Rebalance Metrics (MEDIUM PRIORITY)

**Files to edit:**
- `src/compute/build_metrics.py`

**Columns to add:**
- `nr_gross_chg_1w`, `nr_net_abs_chg_1w`, `nr_rebalance_chg_1w`, `nr_rebalance_share_1w` (4 columns)

**Changes:**
1. After line 282, add conditional NR rebalance block (mirror NC/COMM logic)

**Acceptance criteria:**
- All 4 NR rebalance columns exist when NR data is present
- Formula: `nr_rebalance_chg_1w == nr_gross_chg_1w - nr_net_abs_chg_1w`
- `nr_rebalance_share_1w` in [0, 1] when `nr_gross_chg_1w > 0`

**Risk level:** Medium (depends on Patch 3)

---

### Patch 5: Compute Symmetry - Net Side and Flip Flags (MEDIUM PRIORITY)

**Files to edit:**
- `src/compute/build_metrics.py`

**Columns to add:**
- `nr_net_side` (1 column)
- `nr_net_flip_1w` (1 column)

**Changes:**
1. After line 292, add conditional `nr_net_side`
2. After line 363, add conditional `nr_net_flip_1w`

**Acceptance criteria:**
- `nr_net_side` in {"NET_LONG", "NET_SHORT", "FLAT"}
- `nr_net_flip_1w` is bool, detects sign changes correctly

**Risk level:** Low

---

### Patch 6: Validations Symmetry - All Metric Families (HIGH PRIORITY)

**Files to edit:**
- `src/compute/validations.py`

**Functions to update:**
- `validate_pos_all()` (extend groups list)
- `validate_pos_5y()` (extend groups list)
- `validate_max_min_all()` (extend groups list)
- `validate_max_min_5y()` (extend groups list)
- `validate_chg_1w()` (extend groups list)
- `validate_net_metrics()` (add NR checks)
- `validate_rebalance_metrics()` (add NR prefix)
- `validate_net_side_and_mag_gap()` (add NR net_side)
- `validate_net_flip_flags()` (add NR flip)

**Changes:**
- Extend `groups` lists conditionally based on NR column presence
- Add NR-specific formula checks and bounds checks

**Acceptance criteria:**
- All validation functions check NR metrics when present
- No false positives (NR validations only run if NR columns exist)
- Formula checks pass for NR metrics

**Risk level:** Medium (requires careful integration)

---

### Patch 7: UI Readiness - Data Table (LOW PRIORITY)

**Files to edit:**
- `src/app/pages/overview.py`

**Changes:**
1. Lines 900-943: Add `nr_*` columns to `display_cols` list if they exist

**Acceptance criteria:**
- Data table shows NR columns when present
- No breaking changes if NR columns are missing

**Risk level:** Low

---

### Patch 8: Documentation Update (LOW PRIORITY)

**Files to edit:**
- `README.md`
- `docs/` (if applicable)

**Changes:**
- Document that NR metrics are conditionally computed
- Document that Positioning UI intentionally excludes NR (by design)
- Document that Exposure Shares UI includes NR (when present)

**Acceptance criteria:**
- README accurately describes NR coverage
- Design decisions are documented

**Risk level:** Low

---

## 6) Are We Safe to Build Future Charts/Signals Without NR?

### Answer: **NO** (with caveats)

### Rationale:

**Current State:**
- NR data exists in canonical (`nr_long`, `nr_short`, `nr_net`)
- NR has **only 4 metrics** computed (gross + shares) vs. **~40 metrics** for NC/COMM
- Most compute logic assumes 2 groups (NC vs COMM)
- Most validations assume 2 groups
- UI Positioning blocks assume 2 groups

**Risks if Building Charts/Signals Now:**

1. **Incomplete Data:** Charts that need NR positioning (e.g., "3-way net positioning over time") cannot be built without Patch 1-5.

2. **Breaking Assumptions:** Signals that assume "all trader groups" would miss NR, leading to incomplete analysis.

3. **Future Refactoring:** If NR metrics are added later, existing charts/signals may need refactoring to include NR.

4. **Data Consistency:** Exposure Shares UI already shows NR, but Positioning UI does not. This inconsistency may confuse users.

**Recommendations:**

1. **Before Charts/Signals:**
   - Complete **Patch 1-3** (base metrics, heat-range, WoW changes) — **HIGH PRIORITY**
   - Complete **Patch 6** (validations) — **HIGH PRIORITY**
   - This gives NR full metric parity with NC/COMM

2. **Design Decision:**
   - **Option A:** Keep Positioning UI as 2-group (NC vs COMM), but document that NR is excluded by design
   - **Option B:** Refactor Positioning UI to support 3 groups (NC, COMM, NR) — **HIGH EFFORT**

3. **Charts/Signals Readiness:**
   - After Patch 1-3 + 6: **YES, safe to build** (NR metrics available, even if UI doesn't show them)
   - Before Patch 1-3: **NO, not safe** (incomplete data)

**Conclusion:** Complete compute symmetry (Patches 1-3, 6) before building charts/signals that may need NR data. UI can remain 2-group for Positioning, but metrics must be complete.

---

## Summary Statistics

**Total Missing NR Metrics:** ~36 columns
- Base: 3 (`nr_long`, `nr_short`, `nr_total`)
- Net: 1 (`nr_net`)
- Heat-range ALL: 6
- Heat-range 5Y: 6
- WoW changes: 3
- Net change: 1
- Rebalance: 4
- Net side: 1
- Flip: 1
- **Already computed:** 4 (gross + shares)

**Total Missing Validations:** ~9 functions need NR extensions

**UI Blocks:**
- **NR-aware:** 1 (Exposure Shares)
- **Intentionally excludes NR:** 2 (Asset State, Weekly Change)
- **Would break if NR added:** 1 (Positioning Summary)
- **Could include NR:** 1 (Data Table)

**Estimated Effort:**
- **Patches 1-3 (HIGH PRIORITY):** ~2-3 hours
- **Patch 6 (HIGH PRIORITY):** ~2-3 hours
- **Patches 4-5 (MEDIUM PRIORITY):** ~1-2 hours
- **Patches 7-8 (LOW PRIORITY):** ~30 minutes

**Total:** ~6-9 hours for full NR symmetry

---

**End of Report**


