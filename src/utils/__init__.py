"""Utility modules for CAD Repair Assistant."""

from .logger import log
from .color import get_color_name_from_rgb, extract_color_info
from .image import display_image_from_base64, decode_base64_image, create_thumbnail

__all__ = [
    "log",
    "get_color_name_from_rgb",
    "extract_color_info",
    "display_image_from_base64",
    "decode_base64_image",
    "create_thumbnail",
]
