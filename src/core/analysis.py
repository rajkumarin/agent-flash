"""AI analysis functions for CAD Repair Assistant."""

import os
from typing import List, Dict, Tuple, Optional, Any
import traceback
import base64
from io import BytesIO

import streamlit as st
from PIL import Image

from utils.logger import log
from utils.image import decode_base64_image
from config import FREECAD_VIEW_MAPPING, VIEW_VISIBILITY_INFO
from core.model_context import get_model_context, extract_mentioned_parts
from core.rendering import (
    render_part_image,
    render_model_with_highlights,
    get_basic_screenshot
)
from core.prompts import build_system_prompt, VIEW_DETECTION_PROMPT
from core.response_parser import parse_and_format_response
from core.parts_database import get_stock_image_path


def _image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def load_stock_image(view_angle: str) -> Optional[Image.Image]:
    """
    Load a stock reference image for the given view angle.

    Args:
        view_angle: View angle like "FrontLeft", "RearRight", etc.

    Returns:
        PIL Image or None if not found
    """
    stock_path = get_stock_image_path(view_angle)

    # Try absolute path first (from project root)
    if os.path.exists(stock_path):
        try:
            return Image.open(stock_path)
        except Exception as e:
            log(f"Failed to load stock image from {stock_path}: {e}", "WARNING")

    # Try relative to current working directory
    cwd_path = os.path.join(os.getcwd(), stock_path)
    if os.path.exists(cwd_path):
        try:
            return Image.open(cwd_path)
        except Exception as e:
            log(f"Failed to load stock image from {cwd_path}: {e}", "WARNING")

    # Try finding the src/stock directory
    for base in [".", "..", os.path.dirname(__file__)]:
        check_path = os.path.join(base, stock_path)
        if os.path.exists(check_path):
            try:
                return Image.open(check_path)
            except Exception as e:
                log(f"Failed to load stock image from {check_path}: {e}", "WARNING")

    log(f"Stock image not found for view angle: {view_angle}", "WARNING")
    return None


def _call_gemini(model: Any, prompt: str, images: List[Image.Image] = None) -> str:
    """Call Gemini API with prompt and optional images."""
    if images:
        content = [prompt] + images
        response = model.generate_content(content)
    else:
        response = model.generate_content(prompt)
    return response.text


def _call_claude(
    client: Any,
    model_name: str,
    prompt: str,
    images: List[Image.Image] = None
) -> str:
    """Call Claude API with prompt and optional images."""
    content = []

    # Add images first if provided
    if images:
        for img in images:
            img_b64 = _image_to_base64(img)
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_b64
                }
            })

    # Add text prompt
    content.append({
        "type": "text",
        "text": prompt
    })

    response = client.messages.create(
        model=model_name,
        max_tokens=4096,
        temperature=0,  # Deterministic output
        messages=[
            {"role": "user", "content": content}
        ]
    )

    return response.content[0].text


def _call_ai(prompt: str, images: List[Image.Image] = None) -> str:
    """
    Call the configured AI provider (Gemini or Claude).

    Args:
        prompt: The prompt text
        images: Optional list of PIL Images

    Returns:
        The AI response text
    """
    provider = st.session_state.get("ai_provider", "gemini")

    if provider == "claude":
        client = st.session_state.get("claude_client")
        model_name = st.session_state.get("claude_model")
        if not client:
            raise ValueError("Claude client not configured")
        return _call_claude(client, model_name, prompt, images)
    else:
        # Default to Gemini
        model = st.session_state.get("gemini_model")
        if not model:
            raise ValueError("Gemini model not configured")
        return _call_gemini(model, prompt, images)


def detect_view_angle(user_image: Image.Image) -> str:
    """
    Detect the view angle of the uploaded image using AI.

    Args:
        user_image: PIL Image to analyze

    Returns:
        One of the supported view angles (default: FrontLeft)
    """
    try:
        response_text = _call_ai(VIEW_DETECTION_PROMPT, [user_image])
        detected = response_text.strip().replace(" ", "").replace("-", "")

        # Normalize the response - check for compound views first
        compound_views = ["FrontLeft", "FrontRight", "RearLeft", "RearRight"]
        for view in compound_views:
            if view.lower() in detected.lower():
                return view

        # Then check simple views
        simple_views = ["Front", "Rear", "Left", "Right", "Top"]
        for view in simple_views:
            if view.lower() in detected.lower():
                return view

        # Default to FrontLeft for typical isometric photos
        return "FrontLeft"
    except Exception as e:
        log(f"View detection failed: {e}", "WARNING")
        return "FrontLeft"


def get_visible_parts_filter(
    detected_view: str,
    debug_container=None
) -> Optional[List[Dict]]:
    """
    Get visibility filter for parts based on detected view angle.

    Args:
        detected_view: Detected view angle
        debug_container: Optional Streamlit container for debug messages

    Returns:
        List of visible parts or None to use all parts
    """
    session_has_parts = (
        hasattr(st.session_state, "model_objects")
        and st.session_state.model_objects
    )
    session_parts_count = (
        len(st.session_state.model_objects) if session_has_parts else 0
    )

    if (
        not hasattr(st.session_state, "selected_doc")
        or not hasattr(st.session_state, "mcp_tools")
    ):
        return None

    mcp_tools = st.session_state.mcp_tools
    doc_name = st.session_state.selected_doc

    try:
        result = mcp_tools.get_visible_parts(doc_name, detected_view)
        if result.success and result.data:
            visible_parts_filter = result.data.get("visible_parts", [])
            total_parts = result.data.get('total_parts', 0)
            visible_count = result.data.get('visible_count', 0)

            if debug_container:
                debug_container.write(f"**Total parts from MCP:** {total_parts}")
                debug_container.write(
                    f"**Parts in session state:** {session_parts_count}"
                )
                debug_container.write(
                    f"**Visible parts for {detected_view} view:** {visible_count}"
                )
                hidden_count = result.data.get('hidden_count', 0)
                if hidden_count > 0:
                    hidden_parts = result.data.get('hidden_parts', [])
                    debug_container.write(
                        f"**Hidden/internal parts ({hidden_count}):** "
                        f"{hidden_parts[:5]}{'...' if len(hidden_parts) > 5 else ''}"
                    )

            # If visibility filtering returned 0 parts but we have parts loaded,
            # skip filtering entirely (bounding box data not available)
            if visible_count == 0 and session_parts_count > 0:
                log(
                    f"Visibility filter returned 0 parts but session has "
                    f"{session_parts_count} - skipping filter",
                    "WARNING"
                )
                if debug_container:
                    debug_container.warning(
                        f"Visibility filtering returned 0 parts - "
                        f"using all {session_parts_count} session parts instead"
                    )
                return None

            return visible_parts_filter

    except Exception as e:
        log(f"Could not get visible parts via MCP: {e}", "ERROR")
        if debug_container:
            debug_container.warning(f"Could not get visible parts via MCP: {e}")

    return None


def analyze_image(
    model: Any,
    prompt: str,
    user_image: Optional[Image.Image] = None,
    show_debug: bool = True
) -> Tuple[str, List[Dict], List[str], Optional[Dict[str, Any]]]:
    """
    Analyze user query by comparing the CAD PARTS LIST against the uploaded image.

    Args:
        model: AI model instance (Gemini) - kept for backwards compatibility
        prompt: User's query or notes
        user_image: Optional PIL Image to analyze
        show_debug: Whether to show debug information

    Returns:
        Tuple of (text_response, rendered_images, debug_messages, parsed_data)
    """
    log("Starting image analysis", "INFO")
    debug_messages = []

    # Log which AI provider is being used
    provider = st.session_state.get("ai_provider", "gemini")
    log(f"Using AI provider: {provider}", "INFO")

    # Create a debug expander if needed
    debug_container = (
        st.expander("Debug: Image Rendering", expanded=False)
        if show_debug else None
    )

    # Detect view angle from the uploaded image
    detected_view = "FrontLeft"
    if user_image is not None:
        log("Detecting view angle from uploaded image", "DEBUG")
        detected_view = detect_view_angle(user_image)
        log(f"Detected view angle: {detected_view}", "INFO")
        if debug_container:
            debug_container.write(f"**Detected view angle:** {detected_view}")
            debug_container.write(f"**AI Provider:** {provider}")

    # Get visibility filter
    visible_parts_filter = get_visible_parts_filter(detected_view, debug_container)

    # Final fallback check
    session_has_parts = (
        hasattr(st.session_state, "model_objects")
        and st.session_state.model_objects
    )
    session_parts_count = (
        len(st.session_state.model_objects) if session_has_parts else 0
    )

    if (
        visible_parts_filter is not None
        and len(visible_parts_filter) == 0
        and session_parts_count > 0
    ):
        log(
            f"Final fallback: using {session_parts_count} parts from session state",
            "WARNING"
        )
        visible_parts_filter = None

    # Get model context with visibility filter applied
    model_context, part_names = get_model_context(visible_parts_filter)

    if "No CAD model loaded" in model_context:
        return (
            "Please load a CAD model first by clicking Load Model Parts "
            "in the sidebar.",
            [], [], None
        )

    # Map detected view to FreeCAD render view
    render_view = FREECAD_VIEW_MAPPING.get(detected_view, "Left")
    if debug_container:
        debug_container.write(f"**FreeCAD render view:** {render_view}")

    # Get view info for prompt
    current_view_info = VIEW_VISIBILITY_INFO.get(
        detected_view, "Unknown view angle"
    )

    # Get model name from session state
    model_name = st.session_state.get("selected_doc", "CAD Model")
    log(f"Building prompt for model: {model_name}, view: {detected_view}", "DEBUG")

    # Build the system prompt
    system_prompt = build_system_prompt(model_name, current_view_info, model_context)

    # Load stock reference image for visual comparison
    reference_image = None
    if user_image is not None:
        log(
            f"Loading stock reference image for view: {detected_view}",
            "INFO"
        )
        if debug_container:
            debug_container.write(
                f"**Loading stock reference image for {detected_view} view...**"
            )

        reference_image = load_stock_image(detected_view)
        if reference_image:
            log(
                f"Stock reference image loaded for {detected_view} view",
                "INFO"
            )
            if debug_container:
                debug_container.success(
                    f"[OK] Stock reference image loaded: {get_stock_image_path(detected_view)}"
                )
        else:
            log(f"Stock image not found for {detected_view}, trying CAD screenshot", "WARNING")
            if debug_container:
                debug_container.warning(
                    f"Stock image not found for {detected_view} - trying CAD screenshot fallback"
                )
            # Fallback to CAD screenshot if stock image not available
            cad_image_b64 = get_basic_screenshot(render_view)
            if cad_image_b64:
                reference_image = decode_base64_image(cad_image_b64)
                if reference_image:
                    log("CAD screenshot fallback successful", "INFO")
                    if debug_container:
                        debug_container.success("[OK] CAD screenshot fallback loaded")
                else:
                    log("Failed to decode CAD screenshot fallback", "WARNING")
            else:
                log("CAD screenshot fallback failed", "WARNING")
                if debug_container:
                    debug_container.warning(
                        "Could not load any reference image - "
                        "proceeding with text-only comparison"
                    )

    try:
        # Send BOTH reference image AND user image for visual comparison
        if user_image is not None:
            if reference_image is not None:
                # Visual comparison: Reference first, then user photo
                full_prompt = f"""{system_prompt}

User notes: {prompt}

Compare IMAGE 1 (complete buggy) with IMAGE 2 (user's buggy).
Report any components that are in IMAGE 1 but missing from IMAGE 2.
Output ONLY the JSON response."""
                raw_response = _call_ai(full_prompt, [reference_image, user_image])
                log("Sent visual comparison request with stock reference + user images", "INFO")
            else:
                # Fallback: Text-only comparison if reference image unavailable
                full_prompt = (
                    f"{system_prompt}\n\nUser notes: {prompt}\n\n"
                    "Analyze this image and verify each assembly from the checklist."
                )
                raw_response = _call_ai(full_prompt, [user_image])
                log("Sent text-only comparison (reference image unavailable)", "WARNING")
        else:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}"
            raw_response = _call_ai(full_prompt)

        # Parse structured response and format for display
        text_response, parsed_data, mentioned_parts = parse_and_format_response(
            raw_response, model_name
        )

        # Fallback to legacy extraction if structured parsing failed
        if not mentioned_parts:
            mentioned_parts = extract_mentioned_parts(raw_response, part_names)

        rendered_images = []

        if debug_container:
            debug_container.write(
                f"**Part names in model:** "
                f"{[p['name'] for p in part_names[:10]]}..."
            )
            debug_container.write(
                f"**Mentioned parts found:** "
                f"{mentioned_parts if mentioned_parts else 'None'}"
            )
            debug_container.write(f"**Rendering view:** {detected_view}")
            if parsed_data:
                debug_container.write(
                    f"**Parsed status:** {parsed_data.get('status', 'N/A')}"
                )
                debug_container.write(
                    f"**Confidence:** "
                    f"{parsed_data.get('confidence_score', 0):.0%}"
                )

        if not mentioned_parts:
            if debug_container:
                debug_container.info(
                    "No exact part matches found. Will render model overview."
                )

        # Render images for mentioned parts (max 3)
        for part_name in mentioned_parts[:3]:
            if debug_container:
                debug_container.write(
                    f"---\n**Rendering part: {part_name} ({detected_view} view)**"
                )
            image_b64 = render_part_image(
                part_name, view=render_view, debug_container=debug_container
            )
            if image_b64:
                label = next(
                    (p["label"] for p in part_names if p["name"] == part_name),
                    part_name
                )
                rendered_images.append({
                    "image": image_b64,
                    "caption": f"{label} ({detected_view} view)",
                    "part_name": part_name
                })

        # Always try to render an overview
        if debug_container:
            debug_container.write(
                f"---\n**Rendering model overview "
                f"(FreeCAD {render_view} view) for display reference**"
            )
        overview_b64 = render_model_with_highlights(
            missing_parts=mentioned_parts if mentioned_parts else [],
            view=render_view,
            debug_container=debug_container
        )
        if overview_b64:
            caption = f"CAD Reference - {render_view} view"
            if mentioned_parts:
                caption += " (missing parts highlighted)"
            rendered_images.insert(0, {
                "image": overview_b64,
                "caption": caption,
                "part_name": "overview"
            })

        # Final fallback: basic screenshot
        if len(rendered_images) == 0:
            if debug_container:
                debug_container.write(
                    f"---\n**Fallback: Basic screenshot ({render_view})**"
                )
            fallback_img = get_basic_screenshot(render_view)
            if fallback_img:
                rendered_images.append({
                    "image": fallback_img,
                    "caption": f"CAD Reference ({render_view})",
                    "part_name": "fallback"
                })
                if debug_container:
                    debug_container.success("[OK] Fallback screenshot captured")
            else:
                if debug_container:
                    debug_container.error(
                        "[FAIL] Fallback returned None - check FreeCAD connection"
                    )

        if debug_container:
            debug_container.write(
                f"---\n**Total images rendered: {len(rendered_images)}**"
            )

        return text_response, rendered_images, debug_messages, parsed_data

    except Exception as e:
        error_trace = traceback.format_exc()
        if debug_container:
            debug_container.error(f"Error: {str(e)}\n{error_trace}")
        return f"Error: {str(e)}", [], [], None
