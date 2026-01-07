"""Main Streamlit app entry point (hidden technical page - redirects to market)."""

from __future__ import annotations

import streamlit as st

# Configure page
st.set_page_config(
    page_title="COT Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Redirect to market page (default landing page)
# This page is hidden from navigation but serves as entry point
if "page_initialized" not in st.session_state:
    st.session_state.page_initialized = True
    st.switch_page("pages/market.py")
else:
    st.title("COT Dashboard")
    st.info("This is a technical entry point. Please use the navigation sidebar to access Market or Overview pages.")
