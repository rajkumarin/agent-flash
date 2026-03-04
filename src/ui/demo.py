"""Demo mode UI components for CAD Repair Assistant.

This module is completely separate from the main analysis flow.
It provides a demo experience to showcase how the analysis output looks.
"""

import streamlit as st
from PIL import Image

from config import MAX_THUMBNAIL_WIDTH
from utils.image import create_thumbnail
from core.rendering import render_part_image, render_model_with_highlights
from core.demo import DEMO_PROMPT, DEMO_OUTPUT
from ui.components import display_analysis_report

# Part IDs that make up the Rear Spoiler Assembly
SPOILER_PART_IDS = [
    "6167465",   # Tile 1 x 6 (Lime Green)
    "379528",    # Plate 2 x 6 (Green)
    "6117940",   # Bracket 1 x 2 - 2 x 2 with Rounded Corners (White)
    "4515364",   # Plate 1 x 2 with Bar Handle (White)
    "302201",    # Plate 2 x 2 (White)
    "6264057",   # Plate 3 x 3 with Cut Corner (Lime Green)
]


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


def render_demo_mode() -> None:
    """Render the demo mode UI for uploading and analyzing images."""
    uploaded_file = st.file_uploader(
        "Choose an image",
        type=["jpg", "jpeg", "png", "webp"],
        key="demo_uploader"
    )

    if uploaded_file is not None:
        user_image = Image.open(uploaded_file)

        # Create thumbnail for preview
        display_image = create_thumbnail(user_image, MAX_THUMBNAIL_WIDTH)

        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(display_image, caption="Your Uploaded Image", use_container_width=False)
        with col2:
            st.info(f"Image size: {user_image.width} x {user_image.height} px")

        if st.button("Run Demo Analysis", type="primary"):
            _run_demo_analysis(user_image)

        if hasattr(st.session_state, "demo_result"):
            display_analysis_report(
                st.session_state.demo_result["text"],
                st.session_state.demo_result["images"],
                st.session_state.demo_result.get("user_image"),
                st.session_state.demo_result.get("parsed_data")
            )


def _find_spoiler_parts() -> list[str]:
    """Find all spoiler component parts from loaded model objects."""
    if not hasattr(st.session_state, "model_objects") or not st.session_state.model_objects:
        return []

    spoiler_parts = []

    for obj in st.session_state.model_objects:
        name = obj.get("Name", obj.get("name", ""))
        label = obj.get("Label", obj.get("label", ""))

        # Check if part ID matches any spoiler component
        for part_id in SPOILER_PART_IDS:
            if part_id in name or part_id in label:
                spoiler_parts.append(name)
                break

        # Also check for "spoiler" in name/label
        if "spoiler" in name.lower() or "spoiler" in label.lower():
            if name not in spoiler_parts:
                spoiler_parts.append(name)

    return spoiler_parts


def _run_demo_analysis(user_image: Image.Image) -> None:
    """Run demo analysis by calling AI with guided prompt."""
    if not _is_ai_configured():
        st.warning(_get_ai_warning_message())
        return

    provider = st.session_state.get("ai_provider", "gemini")

    with st.spinner(f"Analyzing image with {provider.title()}..."):
        # Generate the analysis using AI
        text_response = _call_demo_ai(user_image)

        # Find and render highlighted spoiler parts
        images = []
        spoiler_parts = _find_spoiler_parts()

        if spoiler_parts:
            # Render model with spoiler parts highlighted in red
            spoiler_img = render_model_with_highlights(
                missing_parts=spoiler_parts,
                view="RearRight"
            )
            if spoiler_img:
                images.append({
                    "image": spoiler_img,
                    "caption": "Highlighted: Rear Spoiler Assembly"
                })

        st.session_state.demo_result = {
            "text": text_response,
            "images": images,
            "user_image": user_image,
            "parsed_data": None
        }


def _call_demo_ai(user_image: Image.Image) -> str:
    """Call AI provider with demo prompt and user image."""
    import io
    import base64

    provider = st.session_state.get("ai_provider", "gemini")

    # Convert image to bytes for API
    img_buffer = io.BytesIO()
    user_image.save(img_buffer, format="PNG")
    img_bytes = img_buffer.getvalue()

    try:
        if provider == "claude":
            client = st.session_state.claude_client
            model = st.session_state.claude_model

            img_base64 = base64.b64encode(img_bytes).decode("utf-8")

            response = client.messages.create(
                model=model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": img_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": DEMO_PROMPT
                            }
                        ]
                    }
                ]
            )
            return response.content[0].text
        else:
            # Gemini
            model = st.session_state.gemini_model
            response = model.generate_content([DEMO_PROMPT, user_image])
            return response.text

    except Exception as e:
        st.warning(f"AI generation failed: {e}. Using fallback output.")
        return DEMO_OUTPUT
