"""Core modules for CAD Repair Assistant."""

from .model_context import get_model_context, extract_mentioned_parts, get_part_attribute
from .analysis import analyze_image, detect_view_angle
from .rendering import render_part_image, render_model_with_highlights, get_basic_screenshot
from .prompts import build_system_prompt, VIEW_DETECTION_PROMPT

__all__ = [
    "get_model_context",
    "extract_mentioned_parts",
    "get_part_attribute",
    "analyze_image",
    "detect_view_angle",
    "build_system_prompt",
    "VIEW_DETECTION_PROMPT",
    "render_part_image",
    "render_model_with_highlights",
    "get_basic_screenshot",
]
