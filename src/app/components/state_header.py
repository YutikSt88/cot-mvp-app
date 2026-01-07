"""State header component: displays asset state with heatline indicators."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.app.components.heatline import heatline


def render_state_header(df_latest: pd.DataFrame) -> None:
    """
    Render "Температура ринку" header block.
    
    Args:
        df_latest: Single-row DataFrame with latest metrics data for selected market
    """
    if df_latest.empty:
        st.warning("Немає даних для відображення стану активу.")
        return
    
    row = df_latest.iloc[0]
    
    # Header (centered)
    st.markdown("<h3 style='text-align: center;'>Asset State</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Two columns: NC (left) and COMM (right)
    col_nc, col_comm = st.columns(2)
    
    with col_nc:
        st.markdown("<h4 style='margin-bottom: 0.3em;'>Non-Commercials (Large Speculators)</h4>", unsafe_allow_html=True)
        
        # ALL Time section (compact)
        st.markdown("**ALL Time**")
        
        # NC Long (compact)
        heatline(
            label="Long",
            min_val=row["nc_long_min_all"],
            max_val=row["nc_long_max_all"],
            current_val=row["nc_long"],
            pos=row["nc_long_pos_all"],
            compact=True,
        )
        
        # NC Short (compact)
        heatline(
            label="Short",
            min_val=row["nc_short_min_all"],
            max_val=row["nc_short_max_all"],
            current_val=row["nc_short"],
            pos=row["nc_short_pos_all"],
            compact=True,
        )
        
        # NC Total (compact)
        heatline(
            label="Total",
            min_val=row["nc_total_min_all"],
            max_val=row["nc_total_max_all"],
            current_val=row["nc_total"],
            pos=row["nc_total_pos_all"],
            compact=True,
        )
        
        st.markdown("")  # Spacing
        
        # Last 5 Years section
        st.markdown("**Last 5 Years (rolling)**")
        
        # Check if 5Y data is available (pos_5y is NaN)
        nc_long_pos_5y = row["nc_long_pos_5y"]
        nc_short_pos_5y = row["nc_short_pos_5y"]
        nc_total_pos_5y = row["nc_total_pos_5y"]
        
        # NC Long 5Y
        heatline(
            label="Long",
            min_val=row["nc_long_min_5y"],
            max_val=row["nc_long_max_5y"],
            current_val=row["nc_long"],
            pos=nc_long_pos_5y if pd.notna(nc_long_pos_5y) else None,
            disabled=pd.isna(nc_long_pos_5y),
        )
        
        # NC Short 5Y
        heatline(
            label="Short",
            min_val=row["nc_short_min_5y"],
            max_val=row["nc_short_max_5y"],
            current_val=row["nc_short"],
            pos=nc_short_pos_5y if pd.notna(nc_short_pos_5y) else None,
            disabled=pd.isna(nc_short_pos_5y),
        )
        
        # NC Total 5Y
        heatline(
            label="Total",
            min_val=row["nc_total_min_5y"],
            max_val=row["nc_total_max_5y"],
            current_val=row["nc_total"],
            pos=nc_total_pos_5y if pd.notna(nc_total_pos_5y) else None,
            disabled=pd.isna(nc_total_pos_5y),
        )
    
    with col_comm:
        st.markdown("<h4 style='margin-bottom: 0.3em;'>Commercials (Hedgers)</h4>", unsafe_allow_html=True)
        
        # ALL Time section (compact)
        st.markdown("**ALL Time**")
        
        # COMM Long (compact)
        heatline(
            label="Long",
            min_val=row["comm_long_min_all"],
            max_val=row["comm_long_max_all"],
            current_val=row["comm_long"],
            pos=row["comm_long_pos_all"],
            compact=True,
        )
        
        # COMM Short (compact)
        heatline(
            label="Short",
            min_val=row["comm_short_min_all"],
            max_val=row["comm_short_max_all"],
            current_val=row["comm_short"],
            pos=row["comm_short_pos_all"],
            compact=True,
        )
        
        # COMM Total (compact)
        heatline(
            label="Total",
            min_val=row["comm_total_min_all"],
            max_val=row["comm_total_max_all"],
            current_val=row["comm_total"],
            pos=row["comm_total_pos_all"],
            compact=True,
        )
        
        st.markdown("")  # Spacing
        
        # Last 5 Years section
        st.markdown("**Last 5 Years (rolling)**")
        
        # Check if 5Y data is available
        comm_long_pos_5y = row["comm_long_pos_5y"]
        comm_short_pos_5y = row["comm_short_pos_5y"]
        comm_total_pos_5y = row["comm_total_pos_5y"]
        
        # COMM Long 5Y
        heatline(
            label="Long",
            min_val=row["comm_long_min_5y"],
            max_val=row["comm_long_max_5y"],
            current_val=row["comm_long"],
            pos=comm_long_pos_5y if pd.notna(comm_long_pos_5y) else None,
            disabled=pd.isna(comm_long_pos_5y),
        )
        
        # COMM Short 5Y
        heatline(
            label="Short",
            min_val=row["comm_short_min_5y"],
            max_val=row["comm_short_max_5y"],
            current_val=row["comm_short"],
            pos=comm_short_pos_5y if pd.notna(comm_short_pos_5y) else None,
            disabled=pd.isna(comm_short_pos_5y),
        )
        
        # COMM Total 5Y
        heatline(
            label="Total",
            min_val=row["comm_total_min_5y"],
            max_val=row["comm_total_max_5y"],
            current_val=row["comm_total"],
            pos=comm_total_pos_5y if pd.notna(comm_total_pos_5y) else None,
            disabled=pd.isna(comm_total_pos_5y),
        )
    
    st.markdown("---")  # Separator after state header

