"""
CAD Repair Assistant - Main Streamlit Application

AI-powered assistant for identifying missing or damaged parts in CAD models
by comparing uploaded images against FreeCAD reference models.

All FreeCAD interactions go through MCP Tools for consistent behavior.
"""

import streamlit as st

from mcp_tools import FreeCADMCPTools
from utils.logger import log, get_log_file_path
from ui.sidebar import render_sidebar
from ui.tabs import render_analyze_tab, render_parts_tab, render_repair_tab


# Page configuration
st.set_page_config(
    page_title="CAD Repair Assistant",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state() -> None:
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "mcp_tools" not in st.session_state:
        st.session_state.mcp_tools = FreeCADMCPTools()
    if "gemini_model" not in st.session_state:
        st.session_state.gemini_model = None


def main() -> None:
    """Main application entry point."""
    log(f"CAD Repair Assistant started. Logs: {get_log_file_path()}", "INFO")
    init_session_state()

    # Render sidebar
    render_sidebar()

    # Main content
    st.title("CAD Repair Assistant")
    st.markdown("*AI-powered assistant to help debug and identify issues with your LEGO Technic models*")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Analyze Model", "Parts List", "Repair Guide"])

    with tab1:
        render_analyze_tab()

    with tab2:
        render_parts_tab()

    with tab3:
        render_repair_tab()

    st.markdown("---")


if __name__ == "__main__":
    main()
