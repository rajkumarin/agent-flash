"""CAD model context handling for AI analysis."""

import re
from typing import List, Dict, Tuple, Optional

import streamlit as st

from utils.logger import log
from utils.color import extract_color_info


# Keywords for classifying part importance
CRITICAL_KEYWORDS = [
    "wheel", "tire", "axle", "motor", "engine", "steering", "brake",
    "chassis", "frame", "seat", "cockpit", "driver", "cabin"
]

STRUCTURAL_KEYWORDS = [
    "bracket", "connector", "beam", "plate", "pin", "bush", "support",
    "arm", "link", "joint", "hinge", "mount", "holder", "clip",
    "technic", "liftarm", "gear", "cross"
]

COSMETIC_KEYWORDS = [
    "sticker", "decal", "trim", "bumper", "spoiler", "hood", "fender",
    "grille", "light", "lamp", "mirror", "antenna", "exhaust", "pipe",
    "slope", "tile", "wedge", "panel", "windscreen", "window"
]


def classify_part_importance(label: str, part_type: str = "") -> str:
    """
    Classify a part's importance based on its label and type.

    Args:
        label: The part's human-readable label
        part_type: The part's type ID

    Returns:
        One of: "critical", "structural", "cosmetic"
    """
    text = f"{label} {part_type}".lower()

    # Check critical first (highest priority)
    for keyword in CRITICAL_KEYWORDS:
        if keyword in text:
            return "critical"

    # Then structural
    for keyword in STRUCTURAL_KEYWORDS:
        if keyword in text:
            return "structural"

    # Then cosmetic
    for keyword in COSMETIC_KEYWORDS:
        if keyword in text:
            return "cosmetic"

    # Default to structural for unknown parts
    return "structural"


def get_part_attribute(obj: dict, *keys: str, default: str = "Unknown") -> str:
    """
    Get attribute from object, trying multiple key names.

    Handles both uppercase (from RPC) and lowercase (from MCP tools) keys.

    Args:
        obj: Object dictionary
        *keys: Key names to try in order
        default: Default value if no key found

    Returns:
        Value from first matching key or default
    """
    for key in keys:
        value = obj.get(key)
        if value:
            return value
    return default


def get_model_context(visible_parts_filter: Optional[List[Dict]] = None) -> Tuple[str, List[Dict]]:
    """
    Get formatted context of all loaded CAD parts with detailed descriptions.

    Args:
        visible_parts_filter: Optional list of part dicts with 'name' key to filter visible parts.
                             If provided, only parts in this list will be included.

    Returns:
        Tuple of (context_string, part_names_list)
    """
    log("Getting model context", "DEBUG")

    if not hasattr(st.session_state, "model_objects") or not st.session_state.model_objects:
        log("No CAD model loaded", "WARNING")
        return "No CAD model loaded. Please load a model first.", []

    all_objects = st.session_state.model_objects
    total_parts_count = len(all_objects)
    log(f"Total parts in model: {total_parts_count}", "DEBUG")

    # If we have a visibility filter, only include those parts
    is_filtered = visible_parts_filter is not None
    if is_filtered:
        visible_names = {p["name"] for p in visible_parts_filter}
        objects = [
            obj for obj in all_objects
            if get_part_attribute(obj, 'Name', 'name') in visible_names
        ]
        log(f"Filtered to {len(objects)} visible parts", "DEBUG")
    else:
        objects = all_objects

    parts_list = []
    part_names = []

    for idx, obj in enumerate(objects, start=1):
        name = get_part_attribute(obj, 'Name', 'name')
        obj_type = get_part_attribute(
            obj, 'TypeId', 'type', default='Unknown type'
        )
        label = get_part_attribute(obj, 'Label', 'label', default=name)
        color_info = extract_color_info(obj)

        # Classify part importance
        importance = classify_part_importance(label, obj_type)
        importance_tag = {
            "critical": "[CRITICAL]",
            "structural": "[STRUCT]",
            "cosmetic": "[COSMETIC]"
        }.get(importance, "")

        # Build detailed part entry with PART NUMBER for easy reference
        part_entry = f"{idx}. {importance_tag} **{label}** (Part ID: {name})"
        if color_info:
            part_entry += f" [Color: {color_info}]"
        else:
            part_entry += " [Color: Unknown]"

        parts_list.append(part_entry)
        part_names.append({
            "name": name,
            "label": label,
            "color": color_info,
            "part_number": idx,
            "importance": importance
        })

    newline = chr(10)

    if is_filtered:
        context = f"""
VISIBLE PARTS CHECKLIST FOR THIS VIEW ({len(objects)} visible parts, {total_parts_count - len(objects)} hidden/internal parts excluded):
{newline.join(parts_list)}

IMPORTANT: This list contains ONLY the parts that should be visible from the current viewing angle.
Internal parts (like axles inside housings) have been filtered out to prevent false positives.
When reporting missing parts, use the PART NUMBER (e.g., #1, #15) and Part ID for reference.
"""
    else:
        context = f"""
COMPLETE CAD MODEL PARTS CHECKLIST ({len(objects)} parts total):
{newline.join(parts_list)}

IMPORTANT: This is the COMPLETE parts list. Every part listed above MUST be present in a correctly assembled model.
When reporting missing parts, ALWAYS use the PART NUMBER (e.g., #1, #15) and Part ID for accurate reference.
"""
    return context, part_names


def extract_mentioned_parts(text: str, part_names: List[Dict]) -> List[str]:
    """
    Extract part names mentioned in the AI response.

    Args:
        text: AI response text
        part_names: List of part dictionaries with 'name' and 'label' keys

    Returns:
        List of part names that were mentioned
    """
    log("Extracting mentioned parts from AI response", "DEBUG")
    mentioned = []
    text_lower = text.lower()

    for part in part_names:
        name_lower = part["name"].lower()
        label_lower = part["label"].lower()
        if name_lower in text_lower or label_lower in text_lower:
            mentioned.append(part["name"])

    log(f"Found {len(mentioned)} mentioned parts: {mentioned}", "DEBUG")
    return mentioned
