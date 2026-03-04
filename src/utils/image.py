"""Image processing utilities for CAD Repair Assistant."""

import base64
import io
from typing import Optional

import streamlit as st
from PIL import Image


def decode_base64_image(image_b64: str) -> Optional[Image.Image]:
    """
    Decode a base64 encoded image to PIL Image.

    Args:
        image_b64: Base64 encoded image string

    Returns:
        PIL Image object or None if decoding fails
    """
    if not image_b64:
        return None
    try:
        image_bytes = base64.b64decode(image_b64)
        return Image.open(io.BytesIO(image_bytes))
    except Exception:
        return None


def display_image_from_base64(image_b64: str, caption: str = "") -> bool:
    """
    Display a base64 encoded image in Streamlit.

    Args:
        image_b64: Base64 encoded image string
        caption: Optional caption for the image

    Returns:
        True if image was displayed successfully, False otherwise
    """
    image = decode_base64_image(image_b64)
    if image:
        st.image(image, caption=caption, use_container_width=True)
        return True
    return False


def create_thumbnail(image: Image.Image, max_width: int = 400) -> Image.Image:
    """
    Create a thumbnail of an image while maintaining aspect ratio.

    Args:
        image: PIL Image to resize
        max_width: Maximum width in pixels

    Returns:
        Resized PIL Image
    """
    if image.width <= max_width:
        return image.copy()

    ratio = max_width / image.width
    new_size = (max_width, int(image.height * ratio))
    return image.resize(new_size, Image.Resampling.LANCZOS)
