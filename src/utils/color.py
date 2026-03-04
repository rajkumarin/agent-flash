"""Color utilities for CAD Repair Assistant."""

from typing import Tuple


def get_color_name_from_rgb(r: float, g: float, b: float) -> str:
    """
    Determine color name from RGB values (0-1 range).

    Args:
        r: Red component (0-1)
        g: Green component (0-1)
        b: Blue component (0-1)

    Returns:
        Human-readable color name or RGB string
    """
    if r > 0.8 and g > 0.8 and b < 0.3:
        return "YELLOW"
    elif r > 0.8 and g < 0.3 and b < 0.3:
        return "RED"
    elif r < 0.3 and g > 0.8 and b < 0.3:
        return "GREEN"
    elif r < 0.3 and g < 0.3 and b > 0.8:
        return "BLUE"
    elif r > 0.6 and g > 0.6 and b > 0.6:
        return "GREY/LIGHT GREY"
    elif 0.3 < r < 0.6 and 0.3 < g < 0.6 and 0.3 < b < 0.6:
        return "GREY/DARK GREY"
    elif r < 0.3 and g < 0.3 and b < 0.3:
        return "BLACK/VERY DARK"
    elif r > 0.8 and g > 0.4 and b < 0.3:
        return "ORANGE"
    elif r > 0.5 and g > 0.5 and b < 0.3:
        return "YELLOW-GREEN"
    else:
        return f"RGB({r:.2f},{g:.2f},{b:.2f})"


def extract_color_info(obj: dict) -> str:
    """
    Extract color information from a CAD object.

    Handles both RPC format (ViewObject.ShapeColor) and MCP format (color dict).

    Args:
        obj: CAD object dictionary

    Returns:
        Color name string or empty string if no color found
    """
    view_obj = obj.get('ViewObject', {})
    color_dict = obj.get('color', {})

    # Try ViewObject.ShapeColor first (from RPC)
    if 'ShapeColor' in view_obj:
        color = view_obj['ShapeColor']
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            return get_color_name_from_rgb(color[0], color[1], color[2])

    # Try color dict (from MCP tools)
    if color_dict and isinstance(color_dict, dict):
        r = color_dict.get('r', 0)
        g = color_dict.get('g', 0)
        b = color_dict.get('b', 0)
        if r or g or b:
            return get_color_name_from_rgb(r, g, b)

    return ""
