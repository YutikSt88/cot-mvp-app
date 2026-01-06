"""Market page: placeholder for future market-level analytics (default landing page)."""

from __future__ import annotations

import streamlit as st

from src.app.ui_state import render_sidebar

# Configure page
st.set_page_config(
    page_title="COT Dashboard - Market",
    page_icon="📊",
    layout="wide",
)

# Render sidebar with "Go to Overview" button
render_sidebar(current_page="market")

# Page content
st.title("COT Dashboard — Market")

st.info("Market-level analytics will be added in future versions.")
