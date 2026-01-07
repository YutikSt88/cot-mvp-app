"""Heatline component: displays a single heat range indicator."""

from __future__ import annotations

import streamlit as st


def format_number(value: float | int) -> str:
    """Format number with thousand separators, no decimals."""
    if value != value:  # NaN check
        return "N/A"
    return f"{int(value):,}"


def heatline(
    label: str,
    min_val: float,
    max_val: float,
    current_val: float,
    pos: float | None,
    disabled: bool = False,
    compact: bool = False,
) -> None:
    """
    Render a single heatline indicator.
    
    Args:
        label: Label for the line (e.g., "Long", "Short", "Total")
        min_val: Minimum value
        max_val: Maximum value
        current_val: Current value
        pos: Position (0..1) for the dot, or None if disabled
        disabled: If True, show disabled state (gray bar, no dot)
        compact: If True, show compact version without numbers (tooltip only)
    """
    if compact:
        # Compact mode: no numbers column, tooltip on hover
        tooltip_text = f"Min: {format_number(min_val)} | Current: {format_number(current_val)} | Max: {format_number(max_val)}"
        
        # Label (inline with bar)
        st.markdown(f"**{label}**")
        
        if disabled:
            # Disabled state: gray bar, no dot
            st.markdown(
                """
                <div style="
                    height: 18px;
                    width: 70%;
                    background: linear-gradient(to right, #d3d3d3 0%, #d3d3d3 50%, #d3d3d3 100%);
                    border-radius: 3px;
                    position: relative;
                    margin: 2px 0;
                "></div>
                """,
                unsafe_allow_html=True,
            )
            st.caption("Недостатньо історії для 5Y")
        else:
            # Check if min == max (error case)
            if min_val == max_val:
                st.error(f"Помилка: min == max для {label} (значення: {format_number(min_val)})")
                return
            
            # Color gradient: blue (0.0) -> light gray/white (0.5) -> red (1.0)
            # Convert pos to percentage for gradient
            pos_pct = max(0.0, min(1.0, pos or 0.5)) * 100
            
            # Gradient: blue at 0%, light gray/white at 50%, red at 100%
            # Compact: thinner bar, shorter width, with tooltip
            # Escape quotes in tooltip for HTML
            tooltip_escaped = tooltip_text.replace('"', '&quot;')
            gradient_html = f"""
            <div style="
                height: 18px;
                width: 70%;
                background: linear-gradient(to right, 
                    #4A90E2 0%, 
                    #4A90E2 25%,
                    #F5F5F5 50%,
                    #F5F5F5 75%,
                    #E74C3C 100%);
                border-radius: 3px;
                position: relative;
                margin: 2px 0;
                cursor: pointer;
            " title="{tooltip_escaped}">
                <div style="
                    position: absolute;
                    left: {pos_pct}%;
                    top: 50%;
                    transform: translate(-50%, -50%);
                    width: 10px;
                    height: 10px;
                    background-color: #2C3E50;
                    border: 2px solid white;
                    border-radius: 50%;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
                " title="{tooltip_escaped}"></div>
            </div>
            """
            st.markdown(gradient_html, unsafe_allow_html=True)
    else:
        # Full mode: with numbers column
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Label
            st.markdown(f"**{label}**")
            
            if disabled:
                # Disabled state: gray bar, no dot, small text
                st.markdown(
                    """
                    <div style="
                        height: 30px;
                        background: linear-gradient(to right, #d3d3d3 0%, #d3d3d3 50%, #d3d3d3 100%);
                        border-radius: 5px;
                        position: relative;
                        margin: 5px 0;
                    "></div>
                    """,
                    unsafe_allow_html=True,
                )
                st.caption("Недостатньо історії для 5Y")
            else:
                # Check if min == max (error case)
                if min_val == max_val:
                    st.error(f"Помилка: min == max для {label} (значення: {format_number(min_val)})")
                    return
                
                # Color gradient: blue (0.0) -> light gray/white (0.5) -> red (1.0)
                # Convert pos to percentage for gradient
                pos_pct = max(0.0, min(1.0, pos or 0.5)) * 100
                
                # Gradient: blue at 0%, light gray/white at 50%, red at 100%
                # Position marker using percentage
                gradient_html = f"""
                <div style="
                    height: 30px;
                    background: linear-gradient(to right, 
                        #4A90E2 0%, 
                        #4A90E2 25%,
                        #F5F5F5 50%,
                        #F5F5F5 75%,
                        #E74C3C 100%);
                    border-radius: 5px;
                    position: relative;
                    margin: 5px 0;
                ">
                    <div style="
                        position: absolute;
                        left: {pos_pct}%;
                        top: 50%;
                        transform: translate(-50%, -50%);
                        width: 12px;
                        height: 12px;
                        background-color: #2C3E50;
                        border: 2px solid white;
                        border-radius: 50%;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                    "></div>
                </div>
                """
                st.markdown(gradient_html, unsafe_allow_html=True)
        
        with col2:
            # Values
            st.text("")  # Spacing
            st.markdown(f"**Min:** {format_number(min_val)}")
            st.markdown(f"**Current:** {format_number(current_val)}")
            st.markdown(f"**Max:** {format_number(max_val)}")

