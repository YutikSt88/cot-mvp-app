"""UI state management for Streamlit app."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

from src.common.paths import ProjectPaths


@st.cache_data
def get_project_paths():
    """Get project paths (cached)."""
    # On Streamlit Cloud, root is the repo root
    root = Path(".").resolve()
    return ProjectPaths(root)


@st.cache_data
def load_markets_config():
    """Load markets.yaml config (cached)."""
    try:
        paths = get_project_paths()
        config_path = paths.configs / "markets.yaml"
        if not config_path.exists():
            st.warning(f"Markets config not found at: {config_path}")
            return None
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        st.error(f"Error loading markets config: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None


@st.cache_data
def get_categories_and_markets():
    """Get categories and markets grouped by category."""
    config = load_markets_config()
    if config is None:
        return [], {}
    
    markets = config.get("markets", [])
    categories = sorted(set(m.get("category") for m in markets if m.get("category")))
    category_to_markets = {}
    for market in markets:
        category = market.get("category")
        if category:
            if category not in category_to_markets:
                category_to_markets[category] = []
            category_to_markets[category].append(market)
    return categories, category_to_markets


def initialize_selection_defaults():
    """Initialize selection defaults if not set."""
    categories, category_to_markets = get_categories_and_markets()
    
    if not categories:
        return
    
    # Initialize category if not set
    if "selected_category" not in st.session_state:
        st.session_state["selected_category"] = categories[0]
    
    # Initialize asset if not set or invalid
    selected_category = st.session_state.get("selected_category")
    if selected_category and selected_category in category_to_markets:
        markets_in_category = category_to_markets[selected_category]
        market_options = [m.get("market_key") for m in markets_in_category if m.get("market_key")]
        
        if market_options:
            current_asset = st.session_state.get("selected_asset")
            # If current asset is not in the category, pick first available
            if not current_asset or current_asset not in market_options:
                st.session_state["selected_asset"] = market_options[0]
        else:
            st.session_state["selected_asset"] = None
    else:
        st.session_state["selected_asset"] = None


def get_selected_category() -> str | None:
    """Get selected category from session state."""
    initialize_selection_defaults()
    return st.session_state.get("selected_category")


def set_selected_category(category: str) -> None:
    """Set selected category in session state."""
    st.session_state["selected_category"] = category
    # Reset asset when category changes
    categories, category_to_markets = get_categories_and_markets()
    if category in category_to_markets:
        markets_in_category = category_to_markets[category]
        market_options = [m.get("market_key") for m in markets_in_category if m.get("market_key")]
        if market_options:
            st.session_state["selected_asset"] = market_options[0]
        else:
            st.session_state["selected_asset"] = None


def get_selected_asset() -> str | None:
    """Get selected asset (market_key) from session state."""
    initialize_selection_defaults()
    return st.session_state.get("selected_asset")


def set_selected_asset(asset: str) -> None:
    """Set selected asset (market_key) in session state."""
    st.session_state["selected_asset"] = asset


# Legacy alias for compatibility
def get_selected_market_key() -> str | None:
    """Get selected market_key (alias for get_selected_asset)."""
    return get_selected_asset()


def set_selected_market_key(market_key: str) -> None:
    """Set selected market_key (alias for set_selected_asset)."""
    set_selected_asset(market_key)


def render_sidebar(current_page: str = "market") -> None:
    """Render sidebar with category/asset selection and conditional navigation.
    
    Args:
        current_page: Current page name ("market", "overview", etc.)
    """
    categories, category_to_markets = get_categories_and_markets()
    
    if not categories:
        st.sidebar.warning("No markets configured.")
        return
    
    with st.sidebar:
        st.header("Navigation")
        
        # Initialize defaults
        initialize_selection_defaults()
        
        # Category selection
        current_category = get_selected_category()
        category_index = categories.index(current_category) if current_category and current_category in categories else 0
        
        selected_category = st.selectbox(
            "Category",
            options=categories,
            index=category_index if categories else None,
            key="sidebar_category_select",
        )
        
        if selected_category:
            set_selected_category(selected_category)
            
            # Asset selection (filtered by category)
            markets_in_category = category_to_markets.get(selected_category, [])
            market_options = [m.get("market_key") for m in markets_in_category if m.get("market_key")]
            
            if market_options:
                current_asset = get_selected_asset()
                # Validate current asset is in category
                if current_asset and current_asset not in market_options:
                    current_asset = market_options[0]
                    set_selected_asset(current_asset)
                
                asset_index = market_options.index(current_asset) if current_asset and current_asset in market_options else 0
                
                selected_asset = st.selectbox(
                    "Asset",
                    options=market_options,
                    index=asset_index if market_options else None,
                    key="sidebar_asset_select",
                )
                
                if selected_asset:
                    set_selected_asset(selected_asset)
            else:
                set_selected_asset(None)
        
        # Conditional navigation button
        # Note: st.switch_page() cannot be called during initial page render
        # Use Streamlit's built-in page navigation instead
        if current_page != "overview":
            st.markdown("---")
            # Link to overview page using markdown (safer than st.switch_page)
            st.markdown(
                '<a href="/pages/overview" target="_self" style="text-decoration: none;">'
                '<button style="background-color: #FF4B4B; color: white; border: none; '
                'padding: 10px 20px; border-radius: 5px; cursor: pointer; width: 100%;">'
                'Go to Overview</button></a>',
                unsafe_allow_html=True
            )
