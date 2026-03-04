"""Tab UI components for CAD Repair Assistant."""

import json

import streamlit as st
from PIL import Image

from config import COLS_PER_ROW, DEFAULT_REPAIR_PARTS, MAX_THUMBNAIL_WIDTH
from utils.image import display_image_from_base64, create_thumbnail
from core.model_context import (
    get_model_context, extract_mentioned_parts, get_part_attribute
)
from core.rendering import render_part_image, render_model_with_highlights, get_basic_screenshot
from core.analysis import analyze_image
from core.prompts import FULL_ANALYSIS_PROMPT, REPAIR_GUIDE_PROMPT
from ui.components import display_analysis_report
from ui.demo import render_demo_mode


def _is_ai_configured() -> bool:
    """Check if any AI provider is properly configured."""
    provider = st.session_state.get("ai_provider")
    if provider == "claude":
        return st.session_state.get("claude_client") is not None
    else:
        return st.session_state.get("gemini_model") is not None


def _get_ai_warning_message() -> str:
    """Get the appropriate warning message for AI configuration."""
    provider_select = st.session_state.get("ai_provider_select", "Gemini")
    if provider_select == "Claude":
        return "Please configure Claude API key first"
    return "Please configure Gemini API key first"


def render_analyze_tab() -> None:
    """Render the Analyze Model tab."""
    st.header("Upload Image for Analysis")
    st.markdown(
        "Upload an image of your LEGO model. The assistant will compare it "
        "against the CAD reference to help identify any missing or "
        "misassembled parts."
    )

    # Debug mode toggle
    debug_enabled = st.toggle(
        "Enable Debug Mode",
        value=st.session_state.get("debug_mode_enabled", False),
        key="debug_toggle",
        help="Run a demo to see how the analysis output looks"
    )
    st.session_state.debug_mode_enabled = debug_enabled

    if debug_enabled:
        # Debug mode: completely separate demo flow
        render_demo_mode()
    else:
        # Normal mode: user uploads image
        _render_normal_mode()


def _render_normal_mode() -> None:
    """Render the normal mode with user image upload."""
    uploaded_file = st.file_uploader(
        "Choose an image", type=["jpg", "jpeg", "png", "webp"]
    )

    if uploaded_file is not None:
        user_image = Image.open(uploaded_file)

        # Create a thumbnail for display while keeping original for AI
        display_image = create_thumbnail(user_image, MAX_THUMBNAIL_WIDTH)

        # Show smaller preview in a column to control size
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(
                display_image, caption="Your Uploaded Image", use_column_width=False
            )
        with col2:
            st.info(f"Original size: {user_image.width} x {user_image.height} px")

        user_question = st.text_input(
            "Additional inspection notes (optional)",
            placeholder="e.g., Focus on the front assembly, Check wheel attachments"
        )

        if st.button("Analyze Image", type="primary"):
            _run_image_analysis(user_image, user_question)

        if hasattr(st.session_state, "analysis_result"):
            display_analysis_report(
                st.session_state.analysis_result["text"],
                st.session_state.analysis_result["images"],
                st.session_state.analysis_result.get("user_image"),
                st.session_state.analysis_result.get("parsed_data")
            )


def _run_image_analysis(
    user_image: Image.Image,
    user_question: str,
    is_debug: bool = False
) -> None:
    """Run image analysis with configured AI provider."""
    if not _is_ai_configured():
        st.warning(_get_ai_warning_message())
        return

    if (
        not hasattr(st.session_state, "model_objects")
        or not st.session_state.model_objects
    ):
        st.warning(
            "Please load the CAD model first (click Load Model Parts in sidebar)"
        )
        return

    # In debug mode, use the provided prompt directly; otherwise use default
    if is_debug:
        question = user_question  # This is DEMO_PROMPT in debug mode
    else:
        question = user_question if user_question else (
            "What parts are missing or damaged in this image compared to "
            "the complete model?"
        )

    provider = st.session_state.get("ai_provider", "gemini")
    mode_label = "demo" if is_debug else "analysis"
    with st.spinner(f"Running {mode_label} with {provider.title()}..."):
        # Pass gemini_model for backwards compatibility, but analysis.py
        # will use the correct provider based on session state
        model = st.session_state.get("gemini_model")
        text_response, images, _, parsed_data = analyze_image(
            model,
            question,
            user_image
        )

        # In debug mode, render highlighted spoiler image
        if is_debug:
            spoiler_img = render_part_image("rear_spoiler", "RearRight")
            if spoiler_img:
                images.append({
                    "image": spoiler_img,
                    "caption": "Highlighted: Rear Spoiler Assembly"
                })

        st.session_state.analysis_result = {
            "text": text_response,
            "images": images,
            "user_image": user_image,
            "parsed_data": parsed_data
        }


def render_parts_tab() -> None:
    """Render the Parts List tab."""
    st.header("Loaded Model Parts")

    if (
        not hasattr(st.session_state, "model_objects")
        or not st.session_state.model_objects
    ):
        st.info("No model loaded. Click Load Model Parts in the sidebar.")
        return

    objects = st.session_state.model_objects
    st.subheader(f"Found {len(objects)} components")

    # View selector
    view_type = st.selectbox(
        "View Angle", ["Isometric", "Front", "Top", "Right", "Left"]
    )

    # Display parts in a grid with images
    st.markdown("### Click a part to see its 3D render:")

    for i in range(0, len(objects), COLS_PER_ROW):
        cols = st.columns(COLS_PER_ROW)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(objects):
                obj = objects[idx]
                part_name = get_part_attribute(obj, 'Name', 'name')
                label = get_part_attribute(obj, 'Label', 'label', default=part_name)

                with col:
                    if st.button(f"{label}", key=f"part_{idx}_{part_name}"):
                        with st.spinner(f"Rendering {label}..."):
                            img_b64 = render_part_image(part_name, view_type)
                            if img_b64:
                                st.session_state[f"part_img_{part_name}"] = img_b64

                    # Show rendered image if available
                    if f"part_img_{part_name}" in st.session_state:
                        display_image_from_base64(
                            st.session_state[f"part_img_{part_name}"],
                            label
                        )

    st.markdown("---")
    _render_full_analysis_button(objects, view_type)


def _render_full_analysis_button(objects: list, view_type: str) -> None:
    """Render the full AI analysis button and results."""
    if st.button("Run Full AI Analysis", type="primary"):
        if not _is_ai_configured():
            st.warning(_get_ai_warning_message())
            return

        provider = st.session_state.get("ai_provider", "gemini")
        with st.spinner(f"Analyzing model with {provider.title()}..."):
            overview_img = render_model_with_highlights(view=view_type)

            model_context, _ = get_model_context()
            object_summary = json.dumps(objects, indent=2)
            prompt = f"""Analyze this car model:
{object_summary}

Provide:
1. Summary of components
2. Potential missing parts (for a complete car)
3. Recommendations
4. Step-by-step repair guidance"""

            # Use appropriate AI provider
            if provider == "claude":
                from core.analysis import _call_ai
                response_text = _call_ai(f"{FULL_ANALYSIS_PROMPT}\n\n{prompt}")
            else:
                response = st.session_state.gemini_model.generate_content(
                    f"{FULL_ANALYSIS_PROMPT}\n\n{prompt}"
                )
                response_text = response.text

            st.session_state.full_analysis = response_text
            st.session_state.full_analysis_img = overview_img

    if hasattr(st.session_state, "full_analysis"):
        if (
            hasattr(st.session_state, "full_analysis_img")
            and st.session_state.full_analysis_img
        ):
            st.markdown("### Model Overview")
            display_image_from_base64(
                st.session_state.full_analysis_img, "Complete Model View"
            )
        st.markdown("### Analysis")
        st.markdown(st.session_state.full_analysis)


def render_repair_tab() -> None:
    """Render the Repair Guide tab."""
    st.header("Repair Guide")
    st.markdown(
        "Select a part type to get repair instructions with **visual references**."
    )

    part_type = st.selectbox("Missing Part", DEFAULT_REPAIR_PARTS)

    additional_context = st.text_area(
        "Additional context (optional)",
        placeholder="e.g., specific dimensions, material preferences..."
    )

    if st.button("Get Repair Instructions", type="primary"):
        _generate_repair_instructions(part_type, additional_context)

    if hasattr(st.session_state, "repair_result"):
        if st.session_state.repair_result["images"]:
            st.markdown("### Reference Parts from Model")
            cols = st.columns(len(st.session_state.repair_result["images"]))
            for idx, img_data in enumerate(st.session_state.repair_result["images"]):
                with cols[idx]:
                    display_image_from_base64(img_data["image"], img_data["caption"])

        st.markdown("### Repair Instructions")
        st.markdown(st.session_state.repair_result["text"])


def _generate_repair_instructions(part_type: str, additional_context: str) -> None:
    """Generate repair instructions for a part type."""
    if not _is_ai_configured():
        st.warning(_get_ai_warning_message())
        return

    provider = st.session_state.get("ai_provider", "gemini")
    with st.spinner(f"Generating instructions with {provider.title()}..."):
        model_context, part_names = get_model_context()

        system_prompt = REPAIR_GUIDE_PROMPT.format(model_context=model_context)

        prompt = f"""Instructions for adding {part_type} to a car model in FreeCAD.
Context: {additional_context if additional_context else "Standard car"}
Include workbenches, steps, positioning, and tips.
Reference existing similar parts in the model if available."""

        # Use appropriate AI provider
        if provider == "claude":
            from core.analysis import _call_ai
            text_response = _call_ai(f"{system_prompt}\n\n{prompt}")
        else:
            response = st.session_state.gemini_model.generate_content(
                f"{system_prompt}\n\n{prompt}"
            )
            text_response = response.text

        # Try to find and render related parts
        mentioned_parts = extract_mentioned_parts(text_response, part_names)
        images = []
        for part_name in mentioned_parts[:2]:
            img_b64 = render_part_image(part_name)
            if img_b64:
                label = next(
                    (p["label"] for p in part_names if p["name"] == part_name),
                    part_name
                )
                images.append({"image": img_b64, "caption": f"Reference: {label}"})

        st.session_state.repair_result = {
            "text": text_response,
            "images": images
        }
