"""FreeCAD rendering functions for CAD Repair Assistant."""

from typing import Optional, List

import streamlit as st

from utils.logger import log


def render_part_image(
    part_name: str,
    view: str = "Isometric",
    debug_container=None
) -> Optional[str]:
    """
    Render a 2D image of a specific part from FreeCAD using MCP Tools.

    Args:
        part_name: Name of the part to render
        view: View angle
        debug_container: Optional Streamlit container for debug messages

    Returns:
        Base64 encoded image string or None
    """
    log(f"Rendering part image: {part_name}, view: {view}", "INFO")

    if not hasattr(st.session_state, "selected_doc") or not hasattr(st.session_state, "mcp_tools"):
        log("No document selected or MCP tools not initialized", "WARNING")
        if debug_container:
            debug_container.warning("No document selected or MCP tools not initialized")
        return None

    mcp_tools = st.session_state.mcp_tools
    doc_name = st.session_state.selected_doc

    # Method 1: Try get_part_screenshot via MCP proxy
    try:
        if debug_container:
            debug_container.info(f"Trying get_part_screenshot for '{part_name}'...")
        result = mcp_tools.proxy.get_part_screenshot(
            doc_name,
            part_name,
            view,
            [1.0, 0.3, 0.0, 1.0],  # Orange highlight
            False,  # isolate_part
            True    # zoom_to_part
        )

        if result.get("success") and result.get("image"):
            if debug_container:
                debug_container.success(f"[OK] get_part_screenshot succeeded for '{part_name}'")
            return result.get("image")
        else:
            error_msg = result.get("error", "No image returned")
            if debug_container:
                debug_container.warning(f"get_part_screenshot failed: {error_msg}")
    except Exception as e:
        if debug_container:
            debug_container.warning(f"get_part_screenshot exception: {str(e)}")

    # Method 2: Try highlight_part + get_view_screenshot via MCP Tools
    try:
        if debug_container:
            debug_container.info(f"Trying highlight_part + get_view_screenshot for '{part_name}'...")

        highlight_result = mcp_tools.highlight_part(doc_name, part_name, [1.0, 0.3, 0.0, 1.0])

        if highlight_result.success:
            screenshot_result = mcp_tools.get_view_screenshot(doc_name, view)
            # Reset color
            try:
                mcp_tools.proxy.reset_part_color(doc_name, part_name)
            except:
                pass

            if screenshot_result.success and screenshot_result.data:
                if debug_container:
                    debug_container.success(f"[OK] highlight + screenshot succeeded for '{part_name}'")
                return screenshot_result.data.get("image")
        else:
            if debug_container:
                debug_container.warning(f"highlight_part failed: {highlight_result.error}")
    except Exception as e:
        if debug_container:
            debug_container.warning(f"highlight + screenshot exception: {str(e)}")

    # Method 3: Just get a basic screenshot via MCP
    try:
        if debug_container:
            debug_container.info("Trying basic get_view_screenshot...")
        screenshot_result = mcp_tools.get_view_screenshot(doc_name, view)
        if screenshot_result.success and screenshot_result.data:
            if debug_container:
                debug_container.success("[OK] Basic screenshot succeeded")
            return screenshot_result.data.get("image")
    except Exception as e:
        if debug_container:
            debug_container.error(f"All screenshot methods failed: {str(e)}")

    return None


def render_model_with_highlights(
    missing_parts: Optional[List[str]] = None,
    highlight_parts: Optional[List[str]] = None,
    view: str = "Isometric",
    debug_container=None
) -> Optional[str]:
    """
    Render the full model with parts highlighted using MCP Tools.

    Args:
        missing_parts: List of part names to mark as missing
        highlight_parts: List of part names to highlight
        view: View angle
        debug_container: Optional Streamlit container for debug messages

    Returns:
        Base64 encoded image string or None
    """
    log(f"Rendering model overview, view: {view}, missing_parts: {missing_parts}", "INFO")

    if not hasattr(st.session_state, "selected_doc") or not hasattr(st.session_state, "mcp_tools"):
        if debug_container:
            debug_container.warning("No document selected or MCP tools not initialized")
        return None

    mcp_tools = st.session_state.mcp_tools
    doc_name = st.session_state.selected_doc

    # Method 1: Try get_model_overview_screenshot via MCP proxy
    try:
        if debug_container:
            debug_container.info(f"Trying get_model_overview_screenshot with view='{view}', parts={highlight_parts}...")

        result = mcp_tools.proxy.get_model_overview_screenshot(
            doc_name,
            highlight_parts or [],
            missing_parts or [],
            view
        )

        if debug_container:
            debug_container.info(f"RPC call completed, result: {result.get('success')}")

        if result.get("success") and result.get("image"):
            if debug_container:
                debug_container.success("[OK] get_model_overview_screenshot succeeded")
            return result.get("image")
        else:
            error_msg = result.get("error", "No image returned")
            if debug_container:
                debug_container.warning(f"get_model_overview_screenshot failed: {error_msg}")
    except Exception as e:
        if debug_container:
            debug_container.warning(f"get_model_overview_screenshot exception: {str(e)}")

    # Method 2: Just get a regular screenshot via MCP
    try:
        if debug_container:
            debug_container.info("Trying basic get_view_screenshot for overview...")
        screenshot_result = mcp_tools.get_view_screenshot(doc_name, view)
        if screenshot_result.success and screenshot_result.data:
            if debug_container:
                debug_container.success("[OK] Basic overview screenshot succeeded")
            return screenshot_result.data.get("image")
    except Exception as e:
        if debug_container:
            debug_container.error(f"All overview methods failed: {str(e)}")

    return None


def get_basic_screenshot(view: str = "Isometric") -> Optional[str]:
    """
    Get a basic screenshot from FreeCAD.

    Args:
        view: View angle

    Returns:
        Base64 encoded image string or None
    """
    if not hasattr(st.session_state, "selected_doc") or not hasattr(st.session_state, "mcp_tools"):
        return None

    try:
        mcp_tools = st.session_state.mcp_tools
        result = mcp_tools.get_view_screenshot(st.session_state.selected_doc, view)
        if result.success and result.data:
            return result.data.get("image")
    except Exception:
        pass

    return None
