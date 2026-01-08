"""Overview page: full asset report with all analytical blocks."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src.common.paths import ProjectPaths
from src.app.ui_state import (
    get_selected_category,
    get_selected_asset,
    render_sidebar,
    get_categories_and_markets,
)

# Configure page
st.set_page_config(
    page_title="COT Dashboard - Overview",
    page_icon="📊",
    layout="wide",
)

# Render sidebar (no button on overview page)
render_sidebar(current_page="overview")

# Get selected values
selected_category = get_selected_category()
selected_asset = get_selected_asset()

if not selected_asset:
    st.title("COT Dashboard — Overview")
    st.info("Please select a category and asset from the sidebar to view the asset report.")
    st.stop()

# Initialize paths
@st.cache_data
def get_project_paths():
    """Get project paths (cached)."""
    root = Path(".").resolve()
    return ProjectPaths(root)

paths = get_project_paths()

# Find market details
categories, category_to_markets = get_categories_and_markets()
market_info = None
for category, markets_list in category_to_markets.items():
    if category == selected_category:
        for m in markets_list:
            if m.get("market_key") == selected_asset:
                market_info = m
                break
        if market_info:
            break

if market_info is None:
    st.error(f"Asset '{selected_asset}' not found in category '{selected_category}'.")
    st.stop()

# Display header with asset name (left) and week navigation (right)
header_col1, header_col2 = st.columns([3, 1])

with header_col1:
    st.markdown(f"""
    <div style="
        font-size: 2.0em;
        font-weight: 700;
        margin-bottom: 0.5em;
    ">
        {selected_asset}
    </div>
    """, unsafe_allow_html=True)

# Create tabs
tab_pos, tab_oi, tab_charts = st.tabs(["Positioning", "OI", "Charts"])

# Helper function to format numbers
def format_number(value):
    """Format number with thousand separators, no decimals."""
    if pd.isna(value) or value != value:
        return "N/A"
    return f"{int(value):,}"

# Helper function to render a compact heatline bar
def render_heatline_bar(label, min_val, max_val, current_val, pos, disabled=False):
    """Render a single heatline bar with label on the right."""
    if disabled or pd.isna(pos):
        tooltip_text = "Not enough history yet"
        bar_html = f"""
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="
                height: 16px;
                width: 60%;
                background: linear-gradient(to right, #d3d3d3 0%, #d3d3d3 100%);
                border-radius: 3px;
                position: relative;
                margin-right: 10px;
            " title="{tooltip_text}"></div>
            <span style="font-size: 0.9em; font-weight: 500;">{label}</span>
        </div>
        """
    else:
        if min_val == max_val:
            st.error(f"Помилка: min == max для {label}")
            return
        
        pos_pct = max(0.0, min(1.0, pos)) * 100
        tooltip_text = f"Min: {format_number(min_val)} | Current: {format_number(current_val)} | Max: {format_number(max_val)}"
        tooltip_escaped = tooltip_text.replace('"', '&quot;')
        
        bar_html = f"""
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="
                height: 16px;
                width: 60%;
                background: linear-gradient(to right, 
                    #4A90E2 0%, 
                    #4A90E2 25%,
                    #F5F5F5 50%,
                    #F5F5F5 75%,
                    #E74C3C 100%);
                border-radius: 3px;
                position: relative;
                margin-right: 10px;
                cursor: pointer;
            " title="{tooltip_escaped}">
                <div style="
                    position: absolute;
                    left: {pos_pct}%;
                    top: 50%;
                    transform: translate(-50%, -50%);
                    width: 14px;
                    height: 14px;
                    background-color: #2C3E50;
                    border: 2px solid white;
                    border-radius: 50%;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.4);
                " title="{tooltip_escaped}"></div>
            </div>
            <span style="font-size: 0.9em; font-weight: 500;">{label}</span>
        </div>
        """
    
    st.markdown(bar_html, unsafe_allow_html=True)

# Read metrics parquet if exists
metrics_path = paths.data / "compute" / "metrics_weekly.parquet"

if metrics_path.exists():
    try:
        df = pd.read_parquet(metrics_path)
        
        # Ensure report_date is datetime/date (consistent)
        if "report_date" in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["report_date"]):
                df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
        
        # Create df_sorted globally (sorted by market_key and report_date)
        df_sorted = df.sort_values(["market_key", "report_date"]).reset_index(drop=True)
        
        # Filter by market_key
        df_filtered = df[df["market_key"] == selected_asset].copy()
        
        if not df_filtered.empty:
            # Get market_rows for selected asset (sorted ascending by report_date)
            market_rows = df_sorted[df_sorted["market_key"] == selected_asset].sort_values("report_date").reset_index(drop=True)
            
            # Get available weeks for this market (sorted ascending)
            week_dates = market_rows["report_date"].dropna().unique()
            week_dates = sorted(week_dates)
            
            # Initialize session state for week navigation
            session_key_idx = f"week_idx_{selected_asset}"
            session_key_market = f"selected_market_key"
            
            # Reset week index if market changed
            if session_key_market not in st.session_state or st.session_state[session_key_market] != selected_asset:
                st.session_state[session_key_market] = selected_asset
                st.session_state[session_key_idx] = len(week_dates) - 1  # Default to latest week
            
            # Ensure index is valid
            current_idx = st.session_state.get(session_key_idx, len(week_dates) - 1)
            if current_idx < 0:
                current_idx = 0
            if current_idx >= len(week_dates):
                current_idx = len(week_dates) - 1
            st.session_state[session_key_idx] = current_idx
            
            # Get selected week
            selected_week = week_dates[current_idx]
            
            # Get selected_row for selected week (not latest)
            selected_row = market_rows[market_rows["report_date"] == selected_week]
            if not selected_row.empty:
                selected_row = selected_row.iloc[0]
            else:
                # Fallback to latest if selected week not found
                selected_row = market_rows.iloc[-1]
                st.session_state[session_key_idx] = len(week_dates) - 1
                selected_week = week_dates[-1]
            
            # Use selected_row as row for backward compatibility
            row = selected_row
            
            # Render week navigation in header
            with header_col2:
                week_str = selected_week.strftime("%Y-%m-%d") if hasattr(selected_week, 'strftime') else str(selected_week)
                
                # Navigation buttons
                prev_disabled = current_idx == 0
                next_disabled = current_idx == len(week_dates) - 1
                
                nav_col1, nav_col2, nav_col3 = st.columns([1, 3, 1])
                
                with nav_col1:
                    if st.button("◀", disabled=prev_disabled, key="week_prev", use_container_width=True):
                        st.session_state[session_key_idx] = max(0, current_idx - 1)
                        st.rerun()
                
                with nav_col2:
                    st.markdown(f"""
                    <div style="
                        text-align: center;
                        padding-top: 8px;
                    ">
                        <div style="font-size: 0.75em; color: #666; margin-bottom: 2px;">Week</div>
                        <div style="font-size: 0.9em; color: #333; font-weight: 500;">{week_str}</div>
                        <div style="font-size: 0.7em; color: #999; margin-top: 2px;">{current_idx + 1} / {len(week_dates)}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with nav_col3:
                    if st.button("▶", disabled=next_disabled, key="week_next", use_container_width=True):
                        st.session_state[session_key_idx] = min(len(week_dates) - 1, current_idx + 1)
                        st.rerun()
            
            # Inject CSS for compact styling
            st.markdown("""
            <style>
                .asset-header-container {
                    display: flex;
                    justify-content: flex-end;
                    margin-bottom: 0.5em;
                }
                .asset-header {
                    font-size: 1.3em;
                    font-weight: 600;
                    margin: 0;
                }
                .asset-subtitle {
                    font-size: 1.1em;
                    font-weight: 500;
                    margin: 0.2em 0 0 0;
                    text-align: right;
                }
                .compact-divider {
                    margin: 0.3em 0;
                    border-top: 1px solid #e0e0e0;
                }
                .group-header {
                    font-size: 1.05em;
                    font-weight: 600;
                    margin: 0.2em 0 0.5em 0;
                }
                .section-header {
                    font-size: 0.95em;
                    font-weight: 600;
                    margin: 0.5em 0 0.3em 0;
                }
            </style>
            """, unsafe_allow_html=True)
            
            # All content goes into Positioning tab
            with tab_pos:
                # Header: Asset State subtitle
                st.markdown(f"""
                <div style="
                    font-size: 1.1em;
                    font-weight: 500;
                    margin: 0.2em 0 0.5em 0;
                ">
                    Asset State
                </div>
                <div class="compact-divider"></div>
                """, unsafe_allow_html=True)
                
                # Two columns: NC (left) and COMM (right)
                col_nc, col_comm = st.columns(2)
                
                with col_nc:
                    st.markdown('<div class="group-header">Non-Commercials (Large Speculators)</div>', unsafe_allow_html=True)
                    
                    # ALL Time section
                    st.markdown('<div class="section-header">ALL Time</div>', unsafe_allow_html=True)
                    render_heatline_bar("Long", row["nc_long_min_all"], row["nc_long_max_all"], row["nc_long"], row["nc_long_pos_all"])
                    render_heatline_bar("Short", row["nc_short_min_all"], row["nc_short_max_all"], row["nc_short"], row["nc_short_pos_all"])
                    render_heatline_bar("Total", row["nc_total_min_all"], row["nc_total_max_all"], row["nc_total"], row["nc_total_pos_all"])
                    
                    # Last 5 Years section
                    st.markdown('<div class="section-header">Last 5 Years (rolling)</div>', unsafe_allow_html=True)
                    render_heatline_bar("Long", row["nc_long_min_5y"], row["nc_long_max_5y"], row["nc_long"], row["nc_long_pos_5y"], disabled=pd.isna(row["nc_long_pos_5y"]))
                    render_heatline_bar("Short", row["nc_short_min_5y"], row["nc_short_max_5y"], row["nc_short"], row["nc_short_pos_5y"], disabled=pd.isna(row["nc_short_pos_5y"]))
                    render_heatline_bar("Total", row["nc_total_min_5y"], row["nc_total_max_5y"], row["nc_total"], row["nc_total_pos_5y"], disabled=pd.isna(row["nc_total_pos_5y"]))
                
                with col_comm:
                    st.markdown('<div class="group-header">Commercials (Hedgers)</div>', unsafe_allow_html=True)
                    
                    # ALL Time section
                    st.markdown('<div class="section-header">ALL Time</div>', unsafe_allow_html=True)
                    render_heatline_bar("Long", row["comm_long_min_all"], row["comm_long_max_all"], row["comm_long"], row["comm_long_pos_all"])
                    render_heatline_bar("Short", row["comm_short_min_all"], row["comm_short_max_all"], row["comm_short"], row["comm_short_pos_all"])
                    render_heatline_bar("Total", row["comm_total_min_all"], row["comm_total_max_all"], row["comm_total"], row["comm_total_pos_all"])
                    
                    # Last 5 Years section
                    st.markdown('<div class="section-header">Last 5 Years (rolling)</div>', unsafe_allow_html=True)
                    render_heatline_bar("Long", row["comm_long_min_5y"], row["comm_long_max_5y"], row["comm_long"], row["comm_long_pos_5y"], disabled=pd.isna(row["comm_long_pos_5y"]))
                    render_heatline_bar("Short", row["comm_short_min_5y"], row["comm_short_max_5y"], row["comm_short"], row["comm_short_pos_5y"], disabled=pd.isna(row["comm_short_pos_5y"]))
                    render_heatline_bar("Total", row["comm_total_min_5y"], row["comm_total_max_5y"], row["comm_total"], row["comm_total_pos_5y"], disabled=pd.isna(row["comm_total_pos_5y"]))
                
                # Weekly Change (Δ1w) block
                st.markdown('<div class="compact-divider"></div>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="asset-header-container">
                    <div style="text-align: right;">
                        <div class="asset-subtitle">Weekly Change (Δ1w)</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Helper function to render centered change bar
                def render_change_bar(label, value, max_pos_5y, max_neg_5y, report_date_str):
                    """Render a horizontal bar centered at 0 (negative left, positive right)."""
                    if pd.isna(value) or (pd.isna(max_pos_5y) and pd.isna(max_neg_5y)):
                        tooltip_text = "Not enough history yet"
                        bar_html = f"""
                        <div style="display: flex; align-items: center; margin: 3px 0;">
                            <div style="
                                height: 16px;
                                width: 60%;
                                background: linear-gradient(to right, #d3d3d3 0%, #d3d3d3 100%);
                                border-radius: 3px;
                                position: relative;
                                margin-right: 10px;
                            " title="{tooltip_text}"></div>
                            <span style="font-size: 0.9em; font-weight: 500;">{label}</span>
                        </div>
                        """
                    else:
                        # Calculate scale_abs for symmetric positioning
                        scale_abs = max(
                            max_pos_5y if not pd.isna(max_pos_5y) and max_pos_5y > 0 else 0,
                            abs(max_neg_5y) if not pd.isna(max_neg_5y) and max_neg_5y < 0 else 0
                        )
                        if scale_abs == 0:
                            tooltip_text = "Not enough history yet"
                            bar_html = f"""
                            <div style="display: flex; align-items: center; margin: 3px 0;">
                                <div style="
                                    height: 16px;
                                    width: 60%;
                                    background: linear-gradient(to right, #d3d3d3 0%, #d3d3d3 100%);
                                    border-radius: 3px;
                                    position: relative;
                                    margin-right: 10px;
                                " title="{tooltip_text}"></div>
                                <span style="font-size: 0.9em; font-weight: 500;">{label}</span>
                            </div>
                            """
                        else:
                            # Calculate position using symmetric scale
                            pos_pct = 50 + (value / scale_abs * 50)  # 0% to 100%, center at 50%
                            pos_pct = max(0.0, min(100.0, pos_pct))
                            
                            # Calculate intensity using side-aware extremes
                            if value >= 0:
                                if not pd.isna(max_pos_5y) and max_pos_5y > 0:
                                    intensity = (value / max_pos_5y) * 100
                                    intensity_str = f"{intensity:.0f}%"
                                    ref_value_str = f"+{format_number(max_pos_5y)}"
                                    tooltip_text = f"Δ1w: +{format_number(value)} | Week: {report_date_str} | {intensity_str} of 5Y MAX + ({ref_value_str})"
                                else:
                                    tooltip_text = f"Δ1w: +{format_number(value)} | Week: {report_date_str}"
                            else:
                                if not pd.isna(max_neg_5y) and max_neg_5y < 0:
                                    intensity = (value / max_neg_5y) * 100  # value negative, max_neg_5y negative → positive %
                                    intensity_str = f"{intensity:.0f}%"
                                    ref_value_str = format_number(max_neg_5y)  # already negative
                                    tooltip_text = f"Δ1w: {format_number(value)} | Week: {report_date_str} | {intensity_str} of 5Y MAX - ({ref_value_str})"
                                else:
                                    tooltip_text = f"Δ1w: {format_number(value)} | Week: {report_date_str}"
                            
                            tooltip_escaped = tooltip_text.replace('"', '&quot;')
                            
                            # Marker color: green for positive, red for negative
                            bar_color = "#27AE60" if value >= 0 else "#E74C3C"
                            
                            bar_html = f"""
                            <div style="display: flex; align-items: center; margin: 3px 0;">
                                <div style="
                                    height: 16px;
                                    width: 60%;
                                    background: linear-gradient(to right, 
                                        #E74C3C 0%, 
                                        #F5F5F5 50%,
                                        #27AE60 100%);
                                    border-radius: 3px;
                                    position: relative;
                                    margin-right: 10px;
                                    cursor: pointer;
                                " title="{tooltip_escaped}">
                                    <div style="
                                        position: absolute;
                                        left: {pos_pct}%;
                                        top: 50%;
                                        transform: translate(-50%, -50%);
                                        width: 14px;
                                        height: 14px;
                                        background-color: {bar_color};
                                        border: 2px solid white;
                                        border-radius: 50%;
                                        box-shadow: 0 2px 4px rgba(0,0,0,0.4);
                                    " title="{tooltip_escaped}"></div>
                                </div>
                                <span style="font-size: 0.9em; font-weight: 500;">{label}</span>
                            </div>
                            """
                    
                    st.markdown(bar_html, unsafe_allow_html=True)
                
                # Compute scale for last 5 years per metric (up to selected_week)
                five_years_ago = selected_week - timedelta(days=5*365) if hasattr(selected_week, '__sub__') else selected_week
                df_5y = market_rows[(market_rows["report_date"] >= five_years_ago) & (market_rows["report_date"] <= selected_week)].copy()
                
                # Calculate max_pos_5y and max_neg_5y per metric (separate extremes)
                chg_columns = {
                    "nc_long": "nc_long_chg_1w",
                    "nc_short": "nc_short_chg_1w",
                    "comm_long": "comm_long_chg_1w",
                    "comm_short": "comm_short_chg_1w",
                }
                extremes = {}
                for key, col in chg_columns.items():
                    if not df_5y.empty and col in df_5y.columns:
                        col_data = df_5y[col]
                        max_pos = col_data.max() if not col_data.isna().all() else None
                        max_neg = col_data.min() if not col_data.isna().all() else None
                        extremes[key] = {
                            "max_pos_5y": max_pos if not pd.isna(max_pos) and max_pos > 0 else None,
                            "max_neg_5y": max_neg if not pd.isna(max_neg) and max_neg < 0 else None,
                        }
                    else:
                        extremes[key] = {"max_pos_5y": None, "max_neg_5y": None}
                
                # Two columns: NC (left) and COMM (right)
                col_nc_chg, col_comm_chg = st.columns(2)
                
                report_date_str = row["report_date"].strftime("%Y-%m-%d") if hasattr(row["report_date"], 'strftime') else str(row["report_date"])
                
                with col_nc_chg:
                    st.markdown('<div class="group-header">Non-Commercials</div>', unsafe_allow_html=True)
                    nc_long_ext = extremes.get("nc_long", {})
                    render_change_bar("Long", row.get("nc_long_chg_1w"), nc_long_ext.get("max_pos_5y"), nc_long_ext.get("max_neg_5y"), report_date_str)
                    nc_short_ext = extremes.get("nc_short", {})
                    render_change_bar("Short", row.get("nc_short_chg_1w"), nc_short_ext.get("max_pos_5y"), nc_short_ext.get("max_neg_5y"), report_date_str)
                
                with col_comm_chg:
                    st.markdown('<div class="group-header">Commercials</div>', unsafe_allow_html=True)
                    comm_long_ext = extremes.get("comm_long", {})
                    render_change_bar("Long", row.get("comm_long_chg_1w"), comm_long_ext.get("max_pos_5y"), comm_long_ext.get("max_neg_5y"), report_date_str)
                    comm_short_ext = extremes.get("comm_short", {})
                    render_change_bar("Short", row.get("comm_short_chg_1w"), comm_short_ext.get("max_pos_5y"), comm_short_ext.get("max_neg_5y"), report_date_str)
                
                # Positioning Summary (Net Sides / Divergence / Magnitude) block
                st.markdown('<div class="compact-divider"></div>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="asset-header-container">
                    <div style="text-align: right;">
                        <div class="asset-subtitle">Positioning Summary (Net Sides / Divergence / Magnitude)</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Helper function to format net value with sign
                def format_net(value):
                    """Format net value with sign and k notation."""
                    if pd.isna(value) or value != value:
                        return "N/A"
                    abs_val = abs(value)
                    if abs_val >= 1000:
                        return f"{'+' if value >= 0 else ''}{int(value/1000)}k"
                    return f"{'+' if value >= 0 else ''}{int(value)}"
                
                # Section A: Net Sides / Directional Split
                st.markdown('<div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">Net Sides / Directional Split</div>', unsafe_allow_html=True)
            
                nc_net = row.get("nc_net")
                nc_net_chg = row.get("nc_net_chg_1w")
                comm_net = row.get("comm_net")
                comm_net_chg = row.get("comm_net_chg_1w")
                nc_net_side = row.get("nc_net_side")
                comm_net_side = row.get("comm_net_side")
                spec_vs_hedge = row.get("spec_vs_hedge_net")
                spec_vs_hedge_chg = row.get("spec_vs_hedge_net_chg_1w")
                
                # Get previous row for same market_key (for Diverging/Converging calculation and Δ1w)
                prev_spec_vs_hedge = None
                # market_rows already defined above, use it
                market_rows_sorted_desc = market_rows.sort_values("report_date", ascending=False).reset_index(drop=True)
                selected_week_idx_in_market = market_rows_sorted_desc[market_rows_sorted_desc["report_date"] == selected_week].index
                if len(selected_week_idx_in_market) > 0:
                    idx_in_sorted = selected_week_idx_in_market[0]
                    if idx_in_sorted < len(market_rows_sorted_desc) - 1:
                        prev_spec_vs_hedge = market_rows_sorted_desc.iloc[idx_in_sorted + 1]["spec_vs_hedge_net"]
                
                # Calculate Δ1w if not available
                if pd.isna(spec_vs_hedge_chg) and prev_spec_vs_hedge is not None and not pd.isna(prev_spec_vs_hedge) and not pd.isna(spec_vs_hedge):
                    spec_vs_hedge_chg = spec_vs_hedge - prev_spec_vs_hedge
                
                # Determine Diverging/Converging label
                if not pd.isna(spec_vs_hedge) and prev_spec_vs_hedge is not None and not pd.isna(prev_spec_vs_hedge):
                    curr_abs = abs(spec_vs_hedge)
                    prev_abs = abs(prev_spec_vs_hedge)
                    if curr_abs > prev_abs:
                        split_label = "Diverging"
                    elif curr_abs < prev_abs:
                        split_label = "Converging"
                    else:
                        split_label = "Stable"
                else:
                    split_label = "N/A"
                
                # Colors for net sides
                nc_color = "#27AE60" if nc_net_side == "NET_LONG" else "#E74C3C" if nc_net_side == "NET_SHORT" else "#95A5A6"
                comm_color = "#27AE60" if comm_net_side == "NET_LONG" else "#E74C3C" if comm_net_side == "NET_SHORT" else "#95A5A6"
                
                # Single-line summary
                summary_line = f"""
            <div style="margin: 8px 0; font-size: 0.95em; line-height: 1.6;">
                <strong>NC:</strong> 
                <span style="color: {nc_color}; font-weight: 600;">{nc_net_side if not pd.isna(nc_net_side) else 'N/A'}</span>
                <span style="margin-left: 4px;">({format_net(nc_net)}, Δ1w {format_net(nc_net_chg) if not pd.isna(nc_net_chg) else 'N/A'})</span>
                <span style="margin: 0 8px;">|</span>
                <strong>COMM:</strong> 
                <span style="color: {comm_color}; font-weight: 600;">{comm_net_side if not pd.isna(comm_net_side) else 'N/A'}</span>
                <span style="margin-left: 4px;">({format_net(comm_net)}, Δ1w {format_net(comm_net_chg) if not pd.isna(comm_net_chg) else 'N/A'})</span>
                <span style="margin: 0 8px;">|</span>
                <strong>Split:</strong> {format_net(spec_vs_hedge) if not pd.isna(spec_vs_hedge) else 'N/A'}
                <span style="margin-left: 4px;">(Δ1w {format_net(spec_vs_hedge_chg) if not pd.isna(spec_vs_hedge_chg) else 'N/A'}, {split_label})</span>
            </div>
            """
                st.markdown(summary_line, unsafe_allow_html=True)
                
                # Two-dot range line: compute shared scale from last 260 weeks
                df_5y_net = df_filtered.sort_values("report_date", ascending=False).head(260).copy()
                scale_min = None
                scale_max = None
                
                if not df_5y_net.empty:
                    nc_net_5y = df_5y_net["nc_net"].dropna()
                    comm_net_5y = df_5y_net["comm_net"].dropna()
                    
                    all_nets = pd.concat([nc_net_5y, comm_net_5y])
                    if not all_nets.empty:
                        scale_min = all_nets.min()
                        scale_max = all_nets.max()
                
                # Render two-dot range line
                if scale_min is None or scale_max is None or pd.isna(scale_min) or pd.isna(scale_max) or scale_max == scale_min:
                    # Flat range case
                    tooltip_nc = f"NC net: {format_net(nc_net) if not pd.isna(nc_net) else 'N/A'} | Δ1w: {format_net(nc_net_chg) if not pd.isna(nc_net_chg) else 'N/A'} | week: {report_date_str} | Note: flat range"
                    tooltip_comm = f"COMM net: {format_net(comm_net) if not pd.isna(comm_net) else 'N/A'} | Δ1w: {format_net(comm_net_chg) if not pd.isna(comm_net_chg) else 'N/A'} | week: {report_date_str} | Note: flat range"
                    tooltip_nc_escaped = tooltip_nc.replace('"', '&quot;')
                    tooltip_comm_escaped = tooltip_comm.replace('"', '&quot;')
                    
                    range_line_html = f"""
                    <div style="margin: 10px 0;">
                        <div style="
                            height: 3px;
                            width: 60%;
                            background: #d3d3d3;
                            border-radius: 2px;
                            position: relative;
                            margin-bottom: 25px;
                        ">
                            <div style="
                                position: absolute;
                                left: 50%;
                                top: 50%;
                                transform: translate(-50%, -50%);
                                width: 12px;
                                height: 12px;
                                background-color: {nc_color};
                                border: 2px solid white;
                                border-radius: 50%;
                                box-shadow: 0 2px 4px rgba(0,0,0,0.4);
                                cursor: pointer;
                                z-index: 2;
                            " title="{tooltip_nc_escaped}"></div>
                            <div style="
                                position: absolute;
                                left: 50%;
                                top: -18px;
                                transform: translateX(-50%);
                                font-size: 0.7em;
                                color: #666;
                                font-weight: 500;
                                white-space: nowrap;
                            ">NC</div>
                            <div style="
                                position: absolute;
                                left: calc(50% + 16px);
                                top: 50%;
                                transform: translate(-50%, -50%);
                                width: 12px;
                                height: 12px;
                                background-color: {comm_color};
                                border: 2px solid white;
                                border-radius: 50%;
                                box-shadow: 0 2px 4px rgba(0,0,0,0.4);
                                cursor: pointer;
                                z-index: 2;
                            " title="{tooltip_comm_escaped}"></div>
                            <div style="
                                position: absolute;
                                left: calc(50% + 16px);
                                top: -18px;
                                transform: translateX(-50%);
                                font-size: 0.7em;
                                color: #666;
                                font-weight: 500;
                                white-space: nowrap;
                            ">COMM</div>
                        </div>
                    </div>
                    """
                else:
                    # Calculate positions for dots
                    scale_range = scale_max - scale_min
                    if scale_range > 0:
                        nc_pos_pct = ((nc_net - scale_min) / scale_range * 100) if not pd.isna(nc_net) else 50
                        comm_pos_pct = ((comm_net - scale_min) / scale_range * 100) if not pd.isna(comm_net) else 50
                        nc_pos_pct = max(0.0, min(100.0, nc_pos_pct))
                        comm_pos_pct = max(0.0, min(100.0, comm_pos_pct))
                    else:
                        nc_pos_pct = 50
                        comm_pos_pct = 50
                    
                    tooltip_nc = f"NC net: {format_net(nc_net) if not pd.isna(nc_net) else 'N/A'} | Δ1w: {format_net(nc_net_chg) if not pd.isna(nc_net_chg) else 'N/A'} | week: {report_date_str}"
                    tooltip_comm = f"COMM net: {format_net(comm_net) if not pd.isna(comm_net) else 'N/A'} | Δ1w: {format_net(comm_net_chg) if not pd.isna(comm_net_chg) else 'N/A'} | week: {report_date_str}"
                    tooltip_nc_escaped = tooltip_nc.replace('"', '&quot;')
                    tooltip_comm_escaped = tooltip_comm.replace('"', '&quot;')
                    
                    range_line_html = f"""
                <div style="margin: 10px 0;">
                    <div style="
                        height: 3px;
                        width: 60%;
                        background: linear-gradient(to right, #E74C3C 0%, #F5F5F5 50%, #27AE60 100%);
                        border-radius: 2px;
                        position: relative;
                        margin-bottom: 25px;
                    ">
                        <div style="
                            position: absolute;
                            left: {nc_pos_pct}%;
                            top: 50%;
                            transform: translate(-50%, -50%);
                            width: 12px;
                            height: 12px;
                            background-color: {nc_color};
                            border: 2px solid white;
                            border-radius: 50%;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.4);
                            cursor: pointer;
                            z-index: 2;
                        " title="{tooltip_nc_escaped}"></div>
                        <div style="
                            position: absolute;
                            left: {nc_pos_pct}%;
                            top: -18px;
                            transform: translateX(-50%);
                            font-size: 0.7em;
                            color: #666;
                            font-weight: 500;
                            white-space: nowrap;
                        ">NC</div>
                        <div style="
                            position: absolute;
                            left: {comm_pos_pct}%;
                            top: 50%;
                            transform: translate(-50%, -50%);
                            width: 12px;
                            height: 12px;
                            background-color: {comm_color};
                            border: 2px solid white;
                            border-radius: 50%;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.4);
                            cursor: pointer;
                            z-index: 2;
                        " title="{tooltip_comm_escaped}"></div>
                        <div style="
                            position: absolute;
                            left: {comm_pos_pct}%;
                            top: -18px;
                            transform: translateX(-50%);
                            font-size: 0.7em;
                            color: #666;
                            font-weight: 500;
                            white-space: nowrap;
                        ">COMM</div>
                    </div>
                </div>
                """
                
                st.markdown(range_line_html, unsafe_allow_html=True)
                
                # Section B: Magnitude Gap
                st.markdown('<div style="font-size: 0.85em; color: #666; margin-top: 12px; margin-bottom: 5px;">Magnitude Gap</div>', unsafe_allow_html=True)
                
                net_mag_gap = row.get("net_mag_gap")
                net_mag_gap_chg = row.get("net_mag_gap_chg_1w")
                net_mag_gap_pos_5y = row.get("net_mag_gap_pos_5y")
                
                # Determine label
                if not pd.isna(net_mag_gap):
                    if net_mag_gap > 0:
                        mag_label = "Specs more positioned"
                        mag_color = "#27AE60"
                    elif net_mag_gap < 0:
                        mag_label = "Hedgers more positioned"
                        mag_color = "#E74C3C"
                    else:
                        mag_label = "Equal"
                        mag_color = "#95A5A6"
                else:
                    mag_label = "N/A"
                    mag_color = "#95A5A6"
                
                # Render magnitude gap with progress bar
                if pd.isna(net_mag_gap_pos_5y):
                    progress_pct = 0
                    progress_color = "#d3d3d3"
                else:
                    progress_pct = min(100.0, max(0.0, net_mag_gap_pos_5y * 100))
                    progress_color = "#3498DB"
                
                mag_gap_html = f"""
            <div style="margin: 8px 0;">
                <div style="font-size: 0.95em; margin-bottom: 5px;">
                    <strong>Gap:</strong> {format_net(net_mag_gap) if not pd.isna(net_mag_gap) else 'N/A'} | 
                    Δ1w: {format_net(net_mag_gap_chg) if not pd.isna(net_mag_gap_chg) else 'N/A'} | 
                    <span style="color: {mag_color}; font-weight: 500;">{mag_label}</span>
                </div>
                <div style="margin: 5px 0;">
                    <div style="
                        height: 18px;
                        width: 60%;
                        background: #e0e0e0;
                        border-radius: 3px;
                        position: relative;
                        overflow: hidden;
                    ">
                        <div style="
                            height: 100%;
                            width: {progress_pct}%;
                            background: {progress_color};
                            transition: width 0.3s;
                        "></div>
                        <div style="
                            position: absolute;
                            top: 50%;
                            left: 50%;
                            transform: translate(-50%, -50%);
                            font-size: 0.75em;
                            font-weight: 600;
                            color: #333;
                        ">Strength vs 5Y: {progress_pct:.0f}%</div>
                    </div>
                </div>
            </div>
            """
                st.markdown(mag_gap_html, unsafe_allow_html=True)
                
                # Flow Quality (This Week) block
                st.markdown('<div class="compact-divider"></div>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="asset-header-container">
                    <div style="text-align: right;">
                        <div class="asset-subtitle">Flow Quality (This Week)</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Calculate 5Y max(gross) for NC and COMM
                df_5y_flow = df_filtered.sort_values("report_date", ascending=False).head(260).copy()
                nc_gross_max_5y = 1.0
                comm_gross_max_5y = 1.0
                
                if not df_5y_flow.empty:
                    nc_gross_5y = df_5y_flow["nc_gross_chg_1w"].dropna()
                    if not nc_gross_5y.empty:
                        nc_gross_max_5y = max(nc_gross_max_5y, nc_gross_5y.max())
                    
                    comm_gross_5y = df_5y_flow["comm_gross_chg_1w"].dropna()
                    if not comm_gross_5y.empty:
                        comm_gross_max_5y = max(comm_gross_max_5y, comm_gross_5y.max())
                
                # Helper function to render gross activity bar
                def render_gross_bar(gross, gross_max_5y, report_date_str):
                    """Render gross activity progress bar."""
                    if pd.isna(gross) or pd.isna(gross_max_5y) or gross_max_5y == 0:
                        tooltip_text = f"Gross: N/A | 5Y max: {format_net(gross_max_5y) if not pd.isna(gross_max_5y) else 'N/A'} | Week: {report_date_str}"
                        bar_html = f"""
                        <div style="display: flex; align-items: center; margin: 3px 0;">
                            <div style="
                                height: 16px;
                                width: 60%;
                                background: #d3d3d3;
                                border-radius: 3px;
                                position: relative;
                                margin-right: 10px;
                            " title="{tooltip_text.replace('"', '&quot;')}"></div>
                            <span style="font-size: 0.9em;">Gross: N/A</span>
                        </div>
                        """
                    else:
                        gross_pct = min(100.0, (gross / gross_max_5y) * 100)
                        if gross_pct >= 0.67:
                            level = "High"
                            level_color = "#E74C3C"
                        elif gross_pct >= 0.33:
                            level = "Med"
                            level_color = "#F39C12"
                        else:
                            level = "Low"
                            level_color = "#95A5A6"
                        
                        tooltip_text = f"Gross: {format_net(gross)} | 5Y max: {format_net(gross_max_5y)} | Week: {report_date_str}"
                        tooltip_escaped = tooltip_text.replace('"', '&quot;')
                        
                        bar_html = f"""
                        <div style="display: flex; align-items: center; margin: 3px 0;">
                            <div style="
                                height: 16px;
                                width: 60%;
                                background: #e0e0e0;
                                border-radius: 3px;
                                position: relative;
                                margin-right: 10px;
                                cursor: pointer;
                            " title="{tooltip_escaped}">
                                <div style="
                                    height: 100%;
                                    width: {gross_pct}%;
                                    background: #3498DB;
                                    border-radius: 3px;
                                "></div>
                            </div>
                            <span style="font-size: 0.9em;">Gross: {format_net(gross)} <span style="color: {level_color};">({level})</span></span>
                        </div>
                        """
                    
                    st.markdown(bar_html, unsafe_allow_html=True)
            
                # Helper function to render quality stacked bar
                def render_quality_bar(net_chg, net_abs, rebalance, gross, share, flip, report_date_str):
                    """Render quality stacked bar (Real Move vs Rotation)."""
                    if pd.isna(gross) or gross == 0 or pd.isna(net_abs) or pd.isna(rebalance) or pd.isna(share):
                        tooltip_text = f"Net Δ: N/A | Real(|Δnet|): N/A | Rotation: N/A | Gross: N/A | Rotation share: N/A | Week: {report_date_str}"
                        bar_html = f"""
                        <div style="display: flex; align-items: center; margin: 3px 0;">
                            <div style="
                                height: 16px;
                                width: 60%;
                                background: #d3d3d3;
                                border-radius: 3px;
                                position: relative;
                                margin-right: 10px;
                            " title="{tooltip_text.replace('"', '&quot;')}"></div>
                            <span style="font-size: 0.9em;">Real: N/A | Rotation: N/A</span>
                        </div>
                        """
                    else:
                        real_pct = (net_abs / gross * 100) if gross > 0 else 0
                        rot_pct = (rebalance / gross * 100) if gross > 0 else 0
                        
                        # Color for real move based on sign
                        if pd.isna(net_chg) or net_chg == 0:
                            real_color = "#95A5A6"
                        elif net_chg > 0:
                            real_color = "#27AE60"
                        else:
                            real_color = "#E74C3C"
                        
                        reb_color = "#F39C12"
                        
                        # Determine label
                        if share > 0.70:
                            label_text = "Mostly Rotation"
                            label_color = "#F39C12"
                        elif share >= 0.30:
                            label_text = "Mixed"
                            label_color = "#3498DB"
                        else:
                            label_text = "Real Move"
                            label_color = "#27AE60"
                        
                        # FLIP badge
                        flip_badge = ""
                        if flip and not pd.isna(flip) and flip:
                            flip_badge = '<span style="display: inline-block; background: #E74C3C; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.75em; font-weight: 600; margin-left: 8px;">FLIP</span>'
                        
                        tooltip_text = f"Net Δ: {format_net(net_chg) if not pd.isna(net_chg) else 'N/A'} | Real(|Δnet|): {format_net(net_abs)} | Rotation: {format_net(rebalance)} | Gross: {format_net(gross)} | Rotation share: {share*100:.1f}% | Week: {report_date_str}"
                        tooltip_escaped = tooltip_text.replace('"', '&quot;')
                        
                        bar_html = f"""
                        <div style="display: flex; align-items: center; margin: 3px 0;">
                            <div style="
                                height: 16px;
                                width: 60%;
                                background: #2C3E50;
                                border-radius: 3px;
                                position: relative;
                                margin-right: 10px;
                                cursor: pointer;
                            " title="{tooltip_escaped}">
                                <div style="
                                    position: absolute;
                                    left: 0;
                                    top: 0;
                                    height: 100%;
                                    width: {real_pct}%;
                                    background: {real_color};
                                    border-radius: 3px 0 0 3px;
                                "></div>
                                <div style="
                                    position: absolute;
                                    left: {real_pct}%;
                                    top: 0;
                                    height: 100%;
                                    width: {rot_pct}%;
                                    background: {reb_color};
                                    border-radius: 0 3px 3px 0;
                                "></div>
                            </div>
                            <span style="font-size: 0.9em;">Real: {real_pct:.0f}% | Rotation: {rot_pct:.0f}% <span style="color: {label_color}; font-weight: 500;">{label_text}</span>{flip_badge}</span>
                        </div>
                        """
                    
                    st.markdown(bar_html, unsafe_allow_html=True)
            
                # Two columns: NC (left) and COMM (right)
                col_nc_flow, col_comm_flow = st.columns(2)
                
                with col_nc_flow:
                    st.markdown('<div class="group-header">Non-Commercials (NC)</div>', unsafe_allow_html=True)
                    st.markdown('<div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">Gross Activity (vs 5Y)</div>', unsafe_allow_html=True)
                    render_gross_bar(
                        row.get("nc_gross_chg_1w"),
                        nc_gross_max_5y,
                        report_date_str
                    )
                    st.markdown('<div style="font-size: 0.85em; color: #666; margin-top: 8px; margin-bottom: 5px;">Quality: Real Move vs Rotation</div>', unsafe_allow_html=True)
                    render_quality_bar(
                        row.get("nc_net_chg_1w"),
                        row.get("nc_net_abs_chg_1w"),
                        row.get("nc_rebalance_chg_1w"),
                        row.get("nc_gross_chg_1w"),
                        row.get("nc_rebalance_share_1w"),
                        row.get("nc_net_flip_1w"),
                        report_date_str
                    )
                
                with col_comm_flow:
                    st.markdown('<div class="group-header">Commercials (COMM)</div>', unsafe_allow_html=True)
                    st.markdown('<div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">Gross Activity (vs 5Y)</div>', unsafe_allow_html=True)
                    render_gross_bar(
                        row.get("comm_gross_chg_1w"),
                        comm_gross_max_5y,
                        report_date_str
                    )
                    st.markdown('<div style="font-size: 0.85em; color: #666; margin-top: 8px; margin-bottom: 5px;">Quality: Real Move vs Rotation</div>', unsafe_allow_html=True)
                    render_quality_bar(
                        row.get("comm_net_chg_1w"),
                        row.get("comm_net_abs_chg_1w"),
                        row.get("comm_rebalance_chg_1w"),
                        row.get("comm_gross_chg_1w"),
                        row.get("comm_rebalance_share_1w"),
                        row.get("comm_net_flip_1w"),
                        report_date_str
                    )
                
                # Divider after block
                st.markdown('<div class="compact-divider"></div>', unsafe_allow_html=True)
                
                # Divider before table
                st.markdown('<div class="compact-divider"></div>', unsafe_allow_html=True)
                
                # Show last 20 rows table (with net columns)
                display_cols = [
                    "report_date",
                    "nc_long",
                    "nc_short",
                    "nc_long_chg_1w",
                    "nc_short_chg_1w",
                    "comm_long",
                    "comm_short",
                    "comm_long_chg_1w",
                    "comm_short_chg_1w",
                    "nc_net",
                    "comm_net",
                    "spec_vs_hedge_net",
                    "net_mag_gap",
                ]
                
                # Filter to only existing columns and filter by selected_week (show last 20 weeks up to selected week)
                display_cols = [col for col in display_cols if col in market_rows.columns]
                market_rows_up_to_selected = market_rows[market_rows["report_date"] <= selected_week].sort_values("report_date", ascending=False)
                df_display = market_rows_up_to_selected.head(20)[display_cols].copy()
                st.markdown("### 📊 Дані (останні 20 тижнів)")
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                st.caption(f"Showing last 20 rows up to {selected_week.strftime('%Y-%m-%d') if hasattr(selected_week, 'strftime') else selected_week} (total: {len(market_rows)} rows)")
                
                # Debug marker: report continues
                st.caption("Positioning report: end of section ✅")
            
            # OI tab
            with tab_oi:
                # Compact KPI header: 2 cards + week on the right
                oi_chg = row.get("open_interest_chg_1w")
                oi_chg_pct = row.get("open_interest_chg_1w_pct")
                report_date_str = row["report_date"].strftime("%Y-%m-%d") if hasattr(row["report_date"], 'strftime') else str(row["report_date"])
                
                # Format absolute change
                if pd.isna(oi_chg):
                    chg_display = "—"
                    chg_color = "#666"
                else:
                    chg_formatted = format_number(oi_chg)
                    chg_sign = "+" if oi_chg >= 0 else ""
                    chg_display = f"{chg_sign}{chg_formatted}"
                    chg_color = "#27AE60" if oi_chg >= 0 else "#E74C3C"
                
                # Format percentage
                # Show "—" ONLY for NaN/None/inf, NOT for 0
                if pd.isna(oi_chg_pct) or (isinstance(oi_chg_pct, (float, np.floating)) and np.isinf(oi_chg_pct)):
                    pct_display = "—"
                else:
                    # Use + sign format: +X.X% or -X.X%
                    pct_display = f"{oi_chg_pct*100:+.1f}%"
                
                # Create compact KPI cards layout
                k1, k2, spacer, wk = st.columns([1, 1, 4, 1])
                
                with k1:
                    st.markdown(f"""
                    <div style="
                        padding: 8px 12px;
                        background: #f8f9fa;
                        border-radius: 4px;
                        border-left: 3px solid {chg_color};
                    ">
                        <div style="font-size: 0.75em; color: #666; margin-bottom: 2px;">ΔOI 1w</div>
                        <div style="font-size: 1.1em; font-weight: 600; color: {chg_color};">{chg_display}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with k2:
                    st.markdown(f"""
                    <div style="
                        padding: 8px 12px;
                        background: #f8f9fa;
                        border-radius: 4px;
                        border-left: 3px solid {chg_color};
                    ">
                        <div style="font-size: 0.75em; color: #666; margin-bottom: 2px;">ΔOI 1w %</div>
                        <div style="font-size: 1.1em; font-weight: 600; color: {chg_color};">{pct_display}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with wk:
                    st.markdown(f"""
                    <div style="
                        text-align: right;
                        padding-top: 8px;
                    ">
                        <div style="font-size: 0.75em; color: #666;">Week</div>
                        <div style="font-size: 0.85em; color: #333;">{report_date_str}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Header: OI Level subtitle
                st.markdown(f"""
                <div style="
                    font-size: 1.1em;
                    font-weight: 500;
                    margin: 0.2em 0 0.5em 0;
                ">
                    Open Interest Level
                </div>
                <div class="compact-divider"></div>
                """, unsafe_allow_html=True)
                
                # Get OI values from row
                oi_current = row.get("open_interest", 0) if not pd.isna(row.get("open_interest")) else 0
                oi_pos_all = row.get("open_interest_pos_all")
                oi_pos_5y = row.get("open_interest_pos_5y")
                
                # Calculate min/max for ALL Time from market_rows up to selected_week
                if "open_interest" in market_rows.columns:
                    market_oi_data = market_rows[market_rows["report_date"] <= selected_week]["open_interest"]
                    if not market_oi_data.empty:
                        oi_min_all = market_oi_data.min()
                        oi_max_all = market_oi_data.max()
                    else:
                        oi_min_all = oi_current
                        oi_max_all = oi_current
                else:
                    oi_min_all = oi_current
                    oi_max_all = oi_current
                
                # ALL Time section
                st.markdown('<div class="section-header">ALL Time</div>', unsafe_allow_html=True)
                render_heatline_bar("Open Interest", oi_min_all, oi_max_all, oi_current, oi_pos_all if not pd.isna(oi_pos_all) else None)
                
                # Last 5 Years section
                st.markdown('<div class="section-header">Last 5 Years (rolling)</div>', unsafe_allow_html=True)
                # Calculate min/max for 5Y from rolling window
                if pd.isna(oi_pos_5y):
                    render_heatline_bar("Open Interest", 0, 0, oi_current, None, disabled=True)
                else:
                    # Get 5Y rolling window data up to selected_week
                    five_years_ago = selected_week - timedelta(days=5*365) if hasattr(selected_week, '__sub__') else selected_week
                    df_5y_oi = market_rows[
                        (market_rows["report_date"] >= five_years_ago) &
                        (market_rows["report_date"] <= selected_week)
                    ]
                    if not df_5y_oi.empty and "open_interest" in df_5y_oi.columns:
                        oi_min_5y = df_5y_oi["open_interest"].min()
                        oi_max_5y = df_5y_oi["open_interest"].max()
                    else:
                        oi_min_5y = oi_current
                        oi_max_5y = oi_current
                    render_heatline_bar("Open Interest", oi_min_5y, oi_max_5y, oi_current, oi_pos_5y, disabled=pd.isna(oi_pos_5y))
                
                # OI Change Strength (5Y)
                # Use selected week row (row is from selected_week, not latest)
                oi_chg_strength_pos = row.get("open_interest_chg_1w_pct_abs_pos_5y")
                oi_chg_pct_abs = abs(oi_chg_pct) if not pd.isna(oi_chg_pct) else None
                st.markdown('<div class="section-header">OI Change Strength (|ΔOI %|, 5Y)</div>', unsafe_allow_html=True)
                if pd.isna(oi_chg_strength_pos):
                    render_heatline_bar("OI Change Strength", 0, 0, 0, None, disabled=True)
                else:
                    # Render with min=0, max=1, current=pos (already normalized)
                    # Create custom tooltip that shows correct value
                    tooltip_text = f"Min: 0 | Current: {oi_chg_strength_pos:.2f} | Max: 1"
                    tooltip_escaped = tooltip_text.replace('"', '&quot;')
                    pos_pct = max(0.0, min(1.0, oi_chg_strength_pos)) * 100
                    
                    bar_html = f"""
                    <div style="display: flex; align-items: center; margin: 3px 0;">
                        <div style="
                            height: 16px;
                            width: 60%;
                            background: linear-gradient(to right, 
                                #4A90E2 0%, 
                                #4A90E2 25%,
                                #F5F5F5 50%,
                                #F5F5F5 75%,
                                #E74C3C 100%);
                            border-radius: 3px;
                            position: relative;
                            margin-right: 10px;
                            cursor: pointer;
                        " title="{tooltip_escaped}">
                            <div style="
                                position: absolute;
                                left: {pos_pct}%;
                                top: 50%;
                                transform: translate(-50%, -50%);
                                width: 14px;
                                height: 14px;
                                background-color: #2C3E50;
                                border: 2px solid white;
                                border-radius: 50%;
                                box-shadow: 0 2px 4px rgba(0,0,0,0.4);
                            " title="{tooltip_escaped}"></div>
                        </div>
                        <span style="font-size: 0.9em; font-weight: 500;">OI Change Strength</span>
                    </div>
                    """
                    st.markdown(bar_html, unsafe_allow_html=True)
                
                # Exposure Shares (Gross) section
                st.markdown(f"""
                <div style="
                    font-size: 1.1em;
                    font-weight: 500;
                    margin: 1.5em 0 0.5em 0;
                ">
                    Exposure Shares (Gross)
                </div>
                <div class="compact-divider"></div>
                """, unsafe_allow_html=True)
                
                # Check if required columns exist in DataFrame
                required = ["funds_gross_share", "comm_gross_share", "funds_gross_share_chg_1w_pp", "comm_gross_share_chg_1w_pp"]
                optional_nr = ["nr_gross_share", "nr_gross_share_chg_1w_pp"]
                
                # Check if required columns are present
                has_required = all(col in df_filtered.columns for col in required)
                has_nr = all(col in df_filtered.columns for col in optional_nr)
                
                # Get exposure share values from current row
                funds_share = row.get("funds_gross_share")
                comm_share = row.get("comm_gross_share")
                nr_share = row.get("nr_gross_share") if has_nr else None
                
                # Get WoW pp changes
                funds_pp = row.get("funds_gross_share_chg_1w_pp")
                comm_pp = row.get("comm_gross_share_chg_1w_pp")
                nr_pp = row.get("nr_gross_share_chg_1w_pp") if has_nr else None
                
                # Render stacked 100% bar
                if not has_required:
                    st.markdown("""
                    <div style="
                        padding: 12px;
                        background: #f8f9fa;
                        border-radius: 4px;
                        color: #666;
                    ">
                        Exposure shares data not available
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Calculate percentages for display
                    funds_pct = funds_share * 100 if not pd.isna(funds_share) else 0
                    comm_pct = comm_share * 100 if not pd.isna(comm_share) else 0
                    nr_pct = nr_share * 100 if has_nr and not pd.isna(nr_share) else 0
                    
                    # Colors for segments
                    funds_color = "#3498DB"  # Blue
                    comm_color = "#E74C3C"    # Red
                    nr_color = "#95A5A6"      # Gray
                    
                    # Build stacked bar HTML
                    bar_segments = []
                    if funds_pct > 0:
                        bar_segments.append(f'<div style="width: {funds_pct}%; background: {funds_color}; height: 100%; display: inline-block; border-radius: 3px 0 0 3px;" title="Funds: {funds_pct:.1f}%"></div>')
                    if comm_pct > 0:
                        border_radius = "0" if funds_pct > 0 else "3px 0 0 3px"
                        if has_nr and nr_pct > 0:
                            border_radius = "0"
                        bar_segments.append(f'<div style="width: {comm_pct}%; background: {comm_color}; height: 100%; display: inline-block; border-radius: {border_radius};" title="Commercial: {comm_pct:.1f}%"></div>')
                    if has_nr and nr_pct > 0:
                        bar_segments.append(f'<div style="width: {nr_pct}%; background: {nr_color}; height: 100%; display: inline-block; border-radius: 0 3px 3px 0;" title="Nonreportable: {nr_pct:.1f}%"></div>')
                    
                    stacked_bar_html = f"""
                    <div style="
                        display: flex;
                        align-items: center;
                        margin: 8px 0;
                    ">
                        <div style="
                            width: 100%;
                            height: 24px;
                            background: #e0e0e0;
                            border-radius: 3px;
                            display: flex;
                            overflow: hidden;
                        ">
                            {''.join(bar_segments)}
                        </div>
                    </div>
                    <div style="
                        display: flex;
                        justify-content: space-between;
                        font-size: 0.85em;
                        color: #666;
                        margin-top: 4px;
                    ">
                        <span style="color: {funds_color};">Funds {funds_pct:.1f}%</span>
                        <span style="color: {comm_color};">Comm {comm_pct:.1f}%</span>
                        {f'<span style="color: {nr_color};">NR {nr_pct:.1f}%</span>' if has_nr else ''}
                    </div>
                    """
                    st.markdown(stacked_bar_html, unsafe_allow_html=True)
                    
                    # WoW pp change line
                    wow_parts = []
                    if not pd.isna(funds_pp):
                        funds_pp_sign = "+" if funds_pp >= 0 else ""
                        funds_pp_color = "#27AE60" if funds_pp >= 0 else "#E74C3C"
                        wow_parts.append(f'<span style="color: {funds_pp_color};">Funds {funds_pp_sign}{funds_pp:.1f}pp</span>')
                    
                    if not pd.isna(comm_pp):
                        comm_pp_sign = "+" if comm_pp >= 0 else ""
                        comm_pp_color = "#27AE60" if comm_pp >= 0 else "#E74C3C"
                        wow_parts.append(f'<span style="color: {comm_pp_color};">Comm {comm_pp_sign}{comm_pp:.1f}pp</span>')
                    
                    if has_nr and not pd.isna(nr_pp):
                        nr_pp_sign = "+" if nr_pp >= 0 else ""
                        nr_pp_color = "#27AE60" if nr_pp >= 0 else "#E74C3C"
                        wow_parts.append(f'<span style="color: {nr_pp_color};">NR {nr_pp_sign}{nr_pp:.1f}pp</span>')
                    
                    if wow_parts:
                        wow_html = f"""
                        <div style="
                            font-size: 0.85em;
                            color: #666;
                            margin-top: 8px;
                            padding-top: 8px;
                            border-top: 1px solid #e0e0e0;
                        ">
                            <strong>WoW:</strong> {' | '.join(wow_parts)}
                        </div>
                        """
                        st.markdown(wow_html, unsafe_allow_html=True)
                
                # Block 2: Participation / Crowdedness
                st.markdown(f"""
                <div style="
                    font-size: 1.1em;
                    font-weight: 500;
                    margin: 1.5em 0 0.5em 0;
                ">
                    Participation / Crowdedness
                </div>
                <div class="compact-divider"></div>
                """, unsafe_allow_html=True)
                
                # Check if participation columns exist
                has_participation = all(col in df_filtered.columns for col in ["funds_total_pct_oi", "comm_total_pct_oi"])
                has_nr_participation = all(col in df_filtered.columns for col in ["nr_total_pct_oi", "nr_total_pct_oi_chg_1w_pp"])
                
                if has_participation:
                    funds_total_pct = row.get("funds_total_pct_oi")
                    comm_total_pct = row.get("comm_total_pct_oi")
                    funds_total_pct_chg_pp = row.get("funds_total_pct_oi_chg_1w_pp")
                    comm_total_pct_chg_pp = row.get("comm_total_pct_oi_chg_1w_pp")
                    
                    # Create inline metric blocks
                    part_col1, part_col2, part_col3 = st.columns(3)
                    
                    with part_col1:
                        funds_pct_display = f"{funds_total_pct*100:.1f}%" if not pd.isna(funds_total_pct) else "—"
                        funds_chg_display = f"+{funds_total_pct_chg_pp:.1f}pp" if not pd.isna(funds_total_pct_chg_pp) and funds_total_pct_chg_pp >= 0 else f"{funds_total_pct_chg_pp:.1f}pp" if not pd.isna(funds_total_pct_chg_pp) else "—"
                        funds_chg_color = "#27AE60" if not pd.isna(funds_total_pct_chg_pp) and funds_total_pct_chg_pp >= 0 else "#E74C3C"
                        st.markdown(f"""
                        <div style="
                            padding: 16px 20px;
                            background: #f8f9fa;
                            border-radius: 6px;
                            text-align: center;
                        ">
                            <div style="font-size: 0.85em; color: #666; margin-bottom: 6px; font-weight: 500;">Funds</div>
                            <div style="font-size: 38px; font-weight: 700; color: #2C3E50; line-height: 1.1; margin-bottom: 8px;">{funds_pct_display}</div>
                            <div style="font-size: 17px; color: {funds_chg_color}; margin-bottom: 4px; font-weight: 500;">WoW: {funds_chg_display}</div>
                            <div style="font-size: 12px; color: #999; margin-top: 4px;">Share of OI (gross = long+short)</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with part_col2:
                        comm_pct_display = f"{comm_total_pct*100:.1f}%" if not pd.isna(comm_total_pct) else "—"
                        comm_chg_display = f"+{comm_total_pct_chg_pp:.1f}pp" if not pd.isna(comm_total_pct_chg_pp) and comm_total_pct_chg_pp >= 0 else f"{comm_total_pct_chg_pp:.1f}pp" if not pd.isna(comm_total_pct_chg_pp) else "—"
                        comm_chg_color = "#27AE60" if not pd.isna(comm_total_pct_chg_pp) and comm_total_pct_chg_pp >= 0 else "#E74C3C"
                        st.markdown(f"""
                        <div style="
                            padding: 16px 20px;
                            background: #f8f9fa;
                            border-radius: 6px;
                            text-align: center;
                        ">
                            <div style="font-size: 0.85em; color: #666; margin-bottom: 6px; font-weight: 500;">Comm</div>
                            <div style="font-size: 38px; font-weight: 700; color: #2C3E50; line-height: 1.1; margin-bottom: 8px;">{comm_pct_display}</div>
                            <div style="font-size: 17px; color: {comm_chg_color}; margin-bottom: 4px; font-weight: 500;">WoW: {comm_chg_display}</div>
                            <div style="font-size: 12px; color: #999; margin-top: 4px;">Share of OI (gross = long+short)</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with part_col3:
                        if has_nr_participation:
                            nr_total_pct = row.get("nr_total_pct_oi")
                            nr_total_pct_chg_pp = row.get("nr_total_pct_oi_chg_1w_pp")
                            nr_pct_display = f"{nr_total_pct*100:.1f}%" if not pd.isna(nr_total_pct) else "—"
                            nr_chg_display = f"+{nr_total_pct_chg_pp:.1f}pp" if not pd.isna(nr_total_pct_chg_pp) and nr_total_pct_chg_pp >= 0 else f"{nr_total_pct_chg_pp:.1f}pp" if not pd.isna(nr_total_pct_chg_pp) else "—"
                            nr_chg_color = "#27AE60" if not pd.isna(nr_total_pct_chg_pp) and nr_total_pct_chg_pp >= 0 else "#E74C3C"
                            st.markdown(f"""
                            <div style="
                                padding: 16px 20px;
                                background: #f8f9fa;
                                border-radius: 6px;
                                text-align: center;
                            ">
                                <div style="font-size: 0.85em; color: #666; margin-bottom: 6px; font-weight: 500;">NR</div>
                                <div style="font-size: 38px; font-weight: 700; color: #2C3E50; line-height: 1.1; margin-bottom: 8px;">{nr_pct_display}</div>
                                <div style="font-size: 17px; color: {nr_chg_color}; margin-bottom: 4px; font-weight: 500;">WoW: {nr_chg_display}</div>
                                <div style="font-size: 12px; color: #999; margin-top: 4px;">Share of OI (gross = long+short)</div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                else:
                    st.markdown("""
                    <div style="
                        padding: 12px;
                        background: #f8f9fa;
                        border-radius: 4px;
                        color: #666;
                    ">
                        Participation data not available
                    </div>
                    """, unsafe_allow_html=True)
                
                # Block 3: Who Moved (Flows in %OI)
                st.markdown(f"""
                <div style="
                    font-size: 1.1em;
                    font-weight: 500;
                    margin: 1.5em 0 0.5em 0;
                ">
                    Who Moved (Flows in %OI)
                </div>
                <div class="compact-divider"></div>
                """, unsafe_allow_html=True)
                
                # Helper text
                st.caption("Flows = weekly position change divided by last week OI.")
                
                # Check if flow columns exist
                has_flows = all(col in df_filtered.columns for col in ["funds_long_flow_pct_oi", "funds_short_flow_pct_oi", "comm_long_flow_pct_oi", "comm_short_flow_pct_oi"])
                has_nr_flows = all(col in df_filtered.columns for col in ["nr_long_flow_pct_oi", "nr_short_flow_pct_oi"])
                
                if has_flows:
                    # Get flow values
                    funds_long_flow = row.get("funds_long_flow_pct_oi")
                    funds_short_flow = row.get("funds_short_flow_pct_oi")
                    comm_long_flow = row.get("comm_long_flow_pct_oi")
                    comm_short_flow = row.get("comm_short_flow_pct_oi")
                    
                    # NR toggle
                    include_nr = False
                    if has_nr_flows:
                        include_nr = st.toggle("Include NR", value=False)
                    
                    # Format values consistently: +X.XX% with sign and 2 decimals
                    funds_long_display = f"{funds_long_flow*100:+.2f}%" if not pd.isna(funds_long_flow) else "—"
                    funds_short_display = f"{funds_short_flow*100:+.2f}%" if not pd.isna(funds_short_flow) else "—"
                    comm_long_display = f"{comm_long_flow*100:+.2f}%" if not pd.isna(comm_long_flow) else "—"
                    comm_short_display = f"{comm_short_flow*100:+.2f}%" if not pd.isna(comm_short_flow) else "—"
                    
                    funds_long_color = "#27AE60" if not pd.isna(funds_long_flow) and funds_long_flow >= 0 else "#E74C3C"
                    funds_short_color = "#27AE60" if not pd.isna(funds_short_flow) and funds_short_flow >= 0 else "#E74C3C"
                    comm_long_color = "#27AE60" if not pd.isna(comm_long_flow) and comm_long_flow >= 0 else "#E74C3C"
                    comm_short_color = "#27AE60" if not pd.isna(comm_short_flow) and comm_short_flow >= 0 else "#E74C3C"
                    
                    # Create aligned table layout
                    table_html = """
                    <div style="margin: 10px 0;">
                        <table style="width: 100%; border-collapse: collapse; font-size: 0.9em; background: #f8f9fa; border-radius: 6px; overflow: hidden;">
                            <thead>
                                <tr style="background: #2C3E50; color: white;">
                                    <th style="text-align: left; padding: 12px 16px; font-weight: 600; width: 25%;">Group</th>
                                    <th style="text-align: right; padding: 12px 16px; font-weight: 600; width: 37.5%;">Long Flow %OI</th>
                                    <th style="text-align: right; padding: 12px 16px; font-weight: 600; width: 37.5%;">Short Flow %OI</th>
                                </tr>
                            </thead>
                            <tbody>
                    """
                    
                    # Funds row
                    table_html += f"""
                                <tr style="border-bottom: 1px solid #e0e0e0;">
                                    <td style="padding: 12px 16px; color: #3498DB; font-weight: 500;">Funds</td>
                                    <td style="text-align: right; padding: 12px 16px; color: {funds_long_color}; font-weight: 500;">{funds_long_display}</td>
                                    <td style="text-align: right; padding: 12px 16px; color: {funds_short_color}; font-weight: 500;">{funds_short_display}</td>
                                </tr>
                    """
                    
                    # Comm row
                    table_html += f"""
                                <tr style="border-bottom: 1px solid #e0e0e0;">
                                    <td style="padding: 12px 16px; color: #E74C3C; font-weight: 500;">Comm</td>
                                    <td style="text-align: right; padding: 12px 16px; color: {comm_long_color}; font-weight: 500;">{comm_long_display}</td>
                                    <td style="text-align: right; padding: 12px 16px; color: {comm_short_color}; font-weight: 500;">{comm_short_display}</td>
                                </tr>
                    """
                    
                    # NR row (if enabled)
                    if include_nr and has_nr_flows:
                        nr_long_flow = row.get("nr_long_flow_pct_oi")
                        nr_short_flow = row.get("nr_short_flow_pct_oi")
                        nr_long_display = f"{nr_long_flow*100:+.2f}%" if not pd.isna(nr_long_flow) else "—"
                        nr_short_display = f"{nr_short_flow*100:+.2f}%" if not pd.isna(nr_short_flow) else "—"
                        nr_long_color = "#27AE60" if not pd.isna(nr_long_flow) and nr_long_flow >= 0 else "#E74C3C"
                        nr_short_color = "#27AE60" if not pd.isna(nr_short_flow) and nr_short_flow >= 0 else "#E74C3C"
                        table_html += f"""
                                <tr>
                                    <td style="padding: 12px 16px; color: #95A5A6; font-weight: 500;">NR</td>
                                    <td style="text-align: right; padding: 12px 16px; color: {nr_long_color}; font-weight: 500;">{nr_long_display}</td>
                                    <td style="text-align: right; padding: 12px 16px; color: {nr_short_color}; font-weight: 500;">{nr_short_display}</td>
                                </tr>
                        """
                    
                    table_html += """
                            </tbody>
                        </table>
                    </div>
                    """
                    st.markdown(table_html, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="
                        padding: 12px;
                        background: #f8f9fa;
                        border-radius: 4px;
                        color: #666;
                    ">
                        Flow data not available
                    </div>
                    """, unsafe_allow_html=True)
                
                # Block 4: Trend vs Noise
                st.markdown(f"""
                <div style="
                    font-size: 1.1em;
                    font-weight: 500;
                    margin: 1.5em 0 0.5em 0;
                ">
                    Trend vs Noise
                </div>
                <div class="compact-divider"></div>
                """, unsafe_allow_html=True)
                
                # Check if trend columns exist
                has_trend = all(col in df_filtered.columns for col in ["oi_chg_1w_pct", "open_interest_chg_4w_pct", "open_interest_chg_13w_pct"])
                
                if has_trend:
                    oi_chg_1w = row.get("oi_chg_1w_pct")
                    oi_chg_4w = row.get("open_interest_chg_4w_pct")  # Use open_interest_chg_4w_pct for consistency
                    oi_chg_13w = row.get("open_interest_chg_13w_pct")  # Use open_interest_chg_13w_pct for consistency
                    
                    # Create 3 KPI cards
                    trend_col1, trend_col2, trend_col3 = st.columns(3)
                    
                    with trend_col1:
                        chg_1w_display = f"{oi_chg_1w*100:+.1f}%" if not pd.isna(oi_chg_1w) else "—"
                        chg_1w_color = "#27AE60" if not pd.isna(oi_chg_1w) and oi_chg_1w >= 0 else "#E74C3C"
                        st.markdown(f"""
                        <div style="
                            padding: 8px 12px;
                            background: #f8f9fa;
                            border-radius: 4px;
                            border-left: 3px solid {chg_1w_color};
                        ">
                            <div style="font-size: 0.75em; color: #666; margin-bottom: 2px;">1w</div>
                            <div style="font-size: 1.1em; font-weight: 600; color: {chg_1w_color};">{chg_1w_display}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with trend_col2:
                        chg_4w_display = f"{oi_chg_4w*100:+.1f}%" if not pd.isna(oi_chg_4w) else "—"
                        chg_4w_color = "#27AE60" if not pd.isna(oi_chg_4w) and oi_chg_4w >= 0 else "#E74C3C"
                        st.markdown(f"""
                        <div style="
                            padding: 8px 12px;
                            background: #f8f9fa;
                            border-radius: 4px;
                            border-left: 3px solid {chg_4w_color};
                        ">
                            <div style="font-size: 0.75em; color: #666; margin-bottom: 2px;">4w</div>
                            <div style="font-size: 1.1em; font-weight: 600; color: {chg_4w_color};">{chg_4w_display}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with trend_col3:
                        chg_13w_display = f"{oi_chg_13w*100:+.1f}%" if not pd.isna(oi_chg_13w) else "—"
                        chg_13w_color = "#27AE60" if not pd.isna(oi_chg_13w) and oi_chg_13w >= 0 else "#E74C3C"
                        st.markdown(f"""
                        <div style="
                            padding: 8px 12px;
                            background: #f8f9fa;
                            border-radius: 4px;
                            border-left: 3px solid {chg_13w_color};
                        ">
                            <div style="font-size: 0.75em; color: #666; margin-bottom: 2px;">13w</div>
                            <div style="font-size: 1.1em; font-weight: 600; color: {chg_13w_color};">{chg_13w_display}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Trend label: check if 1w, 4w, 13w all have same sign
                    if not pd.isna(oi_chg_1w) and not pd.isna(oi_chg_4w) and not pd.isna(oi_chg_13w):
                        sign_1w = 1 if oi_chg_1w >= 0 else -1
                        sign_4w = 1 if oi_chg_4w >= 0 else -1
                        sign_13w = 1 if oi_chg_13w >= 0 else -1
                        abs_13w = abs(oi_chg_13w)
                        
                        # All three have same sign
                        if sign_1w == sign_4w == sign_13w:
                            trend_label = "Trend"
                            trend_color = "#27AE60" if sign_13w > 0 else "#E74C3C"
                        elif abs_13w < 0.01:
                            trend_label = "Flat"
                            trend_color = "#95A5A6"
                        else:
                            trend_label = "Noise / Mixed"
                            trend_color = "#F39C12"
                        
                        st.markdown(f"""
                        <div style="
                            margin-top: 8px;
                            font-size: 0.85em;
                            color: {trend_color};
                            font-weight: 500;
                        ">
                            {trend_label}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="
                        padding: 12px;
                        background: #f8f9fa;
                        border-radius: 4px;
                        color: #666;
                    ">
                        Trend data not available
                    </div>
                    """, unsafe_allow_html=True)
            
            # Charts tab placeholder
            with tab_charts:
                st.info("Charts tab — coming soon")
        else:
            st.warning(f"Немає даних для ринку '{selected_asset}' в metrics_weekly.parquet")
    except Exception as e:
        st.error(f"Помилка при читанні metrics файлу: {e}")
        import traceback
        st.code(traceback.format_exc())
else:
    st.warning(
        "Немає data/compute/metrics_weekly.parquet. "
        "Запусти: `python -m src.compute.run_compute`"
    )
