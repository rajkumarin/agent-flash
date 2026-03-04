"""Sidebar UI components for CAD Repair Assistant."""

import streamlit as st
import google.generativeai as genai
import anthropic

from config import (
    DEFAULT_HOST, DEFAULT_PORT, GEMINI_MODEL, CLAUDE_MODEL, AI_PROVIDERS
)
from mcp_tools import FreeCADMCPTools
from ui.components import clear_session_cache
from utils.logger import log


def render_sidebar() -> None:
    """Render the sidebar with configuration options."""
    with st.sidebar:
        st.title("CAD Repair Assistant")
        st.markdown("---")

        _render_debug_mode_indicator()
        _render_ai_config()
        st.markdown("---")
        _render_freecad_connection()
        st.markdown("---")
        _render_document_selector()

        if hasattr(st.session_state, "model_objects") and st.session_state.model_objects:
            st.info(f"Model loaded: {len(st.session_state.model_objects)} parts")


def _render_debug_mode_indicator() -> None:
    """Render debug mode status indicator in sidebar."""
    debug_enabled = st.session_state.get("debug_mode_enabled", False)
    if debug_enabled:
        st.success("Demo Mode Active")
        st.markdown("---")


def _render_ai_config() -> None:
    """Render AI API configuration section."""
    st.subheader("AI Configuration")

    # Provider selection - use separate key to avoid conflict
    provider = st.selectbox(
        "AI Provider",
        AI_PROVIDERS,
        key="ai_provider_select"
    )

    if provider == "Gemini":
        _render_gemini_config()
    elif provider == "Claude":
        _render_claude_config()


def _render_gemini_config() -> None:
    """Render Gemini API configuration section."""
    api_key = st.text_input("Google Gemini API Key", type="password", key="gemini_key")

    if api_key:
        try:
            genai.configure(api_key=api_key)
            # Use temperature=0 for consistent, deterministic results
            generation_config = genai.GenerationConfig(
                temperature=0,
                top_p=1,
                top_k=1
            )
            st.session_state.gemini_model = genai.GenerativeModel(
                GEMINI_MODEL,
                generation_config=generation_config
            )
            st.session_state.ai_provider = "gemini"
            st.success(f"Gemini configured ({GEMINI_MODEL})")
        except Exception as e:
            st.error(f"Failed: {e}")


def _render_claude_config() -> None:
    """Render Claude API configuration section."""
    api_key = st.text_input("Anthropic API Key", type="password", key="claude_key")

    if api_key:
        try:
            client = anthropic.Anthropic(api_key=api_key)
            st.session_state.claude_client = client
            st.session_state.claude_model = CLAUDE_MODEL
            st.session_state.ai_provider = "claude"
            st.success(f"Claude configured ({CLAUDE_MODEL})")
        except Exception as e:
            st.error(f"Failed: {e}")


def _render_freecad_connection() -> None:
    """Render FreeCAD connection configuration section."""
    st.subheader("FreeCAD Connection (via MCP)")

    col1, col2 = st.columns(2)
    with col1:
        host = st.text_input("Host", value=DEFAULT_HOST)
    with col2:
        port = st.number_input(
            "Port", value=DEFAULT_PORT, min_value=1, max_value=65535
        )

    # Update MCP tools with connection settings
    st.session_state.mcp_tools = FreeCADMCPTools(host, int(port))

    if st.button("Test Connection"):
        if st.session_state.mcp_tools.ping():
            st.success("Connected to FreeCAD via MCP")
        else:
            st.error("Cannot connect. Start FreeCAD and RPC Server.")


def _render_document_selector() -> None:
    """Render document selection section."""
    st.subheader("Documents")

    # Get list of documents using MCP tool
    docs_result = st.session_state.mcp_tools.list_documents()
    docs = docs_result.data.get("documents", []) if docs_result.success else []

    if docs:
        selected_doc = st.selectbox("Select Document", docs, key="doc_selector")

        # Detect if document changed - clear cache if so
        previous_doc = st.session_state.get("selected_doc", None)
        if previous_doc != selected_doc:
            clear_session_cache()

        st.session_state.selected_doc = selected_doc

        if st.button("Load Model Parts", type="primary"):
            _load_model_parts(selected_doc)
    else:
        st.info("No documents open in FreeCAD")
        if st.button("Create New Document"):
            _create_new_document()


def _load_model_parts(doc_name: str) -> None:
    """Load model parts from FreeCAD document."""
    parts_result = st.session_state.mcp_tools.get_all_parts(doc_name)
    log(f"Parts result: {parts_result}", "DEBUG")
    if parts_result.success:
        objects = parts_result.data.get("parts", [])
        log(f"Loaded objects: {objects}", "DEBUG")
        st.session_state.model_objects = objects

        # Clear cached analysis results when loading a new model
        clear_session_cache()
        # Re-set model_objects since clear_session_cache removes it
        st.session_state.model_objects = objects

        st.success(f"Loaded {len(objects)} parts from '{doc_name}'")


def _create_new_document() -> None:
    """Create a new FreeCAD document."""
    try:
        result = st.session_state.mcp_tools.proxy.create_document("CarModel")
        if result.get("success"):
            st.rerun()
    except Exception as e:
        st.error(f"Failed to create document: {e}")
