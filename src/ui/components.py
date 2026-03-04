"""Reusable UI components for CAD Repair Assistant."""

from typing import List, Dict, Optional

import streamlit as st
from PIL import Image

from utils.image import display_image_from_base64


def display_analysis_report(
    text_response: str,
    images: List[Dict],
    user_image: Optional[Image.Image] = None,
    parsed_data: Optional[Dict] = None
) -> None:
    """
    Display analysis report with Input/Output format.

    Args:
        text_response: AI analysis text (formatted markdown)
        images: List of rendered image dictionaries
        user_image: Optional uploaded user image
        parsed_data: Optional parsed structured data for status display
    """
    # Section 1: Status Banner (if we have parsed data)
    if parsed_data:
        status = parsed_data.get("status", "")
        confidence = parsed_data.get("confidence_score", 0)

        if status == "DEFECT_FREE":
            st.success(
                f"**Status: ALL PARTS PRESENT** | "
                f"Confidence: {confidence:.0%}"
            )
        elif status == "MISSING_PARTS":
            missing = parsed_data.get("missing_assemblies", [])
            st.warning(
                f"**Status: MISSING PARTS DETECTED** | "
                f"{len(missing)} assembly(s) missing | "
                f"Confidence: {confidence:.0%}"
            )
        elif status == "IMAGE_MISMATCH":
            st.error("**Status: IMAGE MISMATCH** - Please upload correct image")

    # Section 2: Input/Output Images Side-by-Side
    st.markdown("---")
    st.markdown("## Input / Output Comparison")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Input (Your Photo):**")
        if user_image is not None:
            st.image(
                user_image,
                caption="Uploaded Image",
                use_container_width=True
            )
        else:
            st.info("No input image")

    with col2:
        st.markdown("**CAD Reference:**")
        if images and len(images) > 0:
            overview_img = images[0]
            display_image_from_base64(
                overview_img["image"],
                "CAD Model Reference"
            )
        else:
            st.info("No CAD reference available")

    st.markdown("---")

    # Section 3: Output - Analysis Report
    st.markdown("## Analysis Report")
    st.markdown(text_response)

    # Section 4: Additional Visual References (if multiple parts identified)
    if images and len(images) > 1:
        st.markdown("---")
        st.markdown("### Visual References for Identified Parts")

        remaining_images = images[1:]
        cols = st.columns(min(len(remaining_images), 3))
        for idx, img_data in enumerate(remaining_images):
            with cols[idx % 3]:
                display_image_from_base64(
                    img_data["image"],
                    img_data["caption"]
                )

    # Section 5: Quick Summary Stats (if parsed data available)
    if parsed_data and parsed_data.get("status") == "MISSING_PARTS":
        missing_assemblies = parsed_data.get("missing_assemblies", [])

        if missing_assemblies:
            st.markdown("---")
            st.markdown("### Issues Summary")

            # Group by importance
            critical = [
                a for a in missing_assemblies
                if a.get("importance") == "critical"
            ]
            structural = [
                a for a in missing_assemblies
                if a.get("importance") == "structural"
            ]
            cosmetic = [
                a for a in missing_assemblies
                if a.get("importance") == "cosmetic"
            ]

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Critical", len(critical))
            with col2:
                st.metric("Structural", len(structural))
            with col3:
                st.metric("Cosmetic", len(cosmetic))

            # Show list of missing assemblies with their parts
            st.markdown("### Missing Assemblies")
            for assembly in missing_assemblies:
                name = assembly.get("assembly_name", "Unknown")
                importance = assembly.get("importance", "").upper()
                parts_needed = assembly.get("parts_needed", [])

                with st.expander(f"{importance}: {name}"):
                    if assembly.get("location"):
                        st.write(f"**Location:** {assembly['location']}")

                    if parts_needed:
                        st.write("**Parts Required:**")
                        for part in parts_needed:
                            num = part.get('part_number', '?')
                            pname = part.get('part_name', 'Unknown')
                            st.write(f"- Part #{num}: {pname}")

                    repair_steps = assembly.get("repair_steps", [])
                    if repair_steps:
                        st.write("**Repair Steps:**")
                        for step in repair_steps:
                            st.write(step)


def clear_session_cache() -> None:
    """Clear all cached analysis results from session state."""
    keys_to_clear = [
        "analysis_result",
        "full_analysis",
        "full_analysis_img",
        "repair_result",
        "model_objects",
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    # Clear individual part images
    keys_to_delete = [k for k in st.session_state.keys() if k.startswith("part_img_")]
    for k in keys_to_delete:
        del st.session_state[k]
