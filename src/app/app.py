"""Main Streamlit app entry point (default landing page - shows Market page content)."""

from __future__ import annotations

import streamlit as st

from src.app.ui_state import render_sidebar

# Configure page
st.set_page_config(
    page_title="COT Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Render sidebar with "Go to Overview" button
render_sidebar(current_page="market")

# Page content (same as market.py)
st.title("COT Dashboard — Market")

st.info("Market-level analytics will be added in future versions.")
