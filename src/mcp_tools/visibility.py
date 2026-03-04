"""Visibility filtering logic for MCP Tools."""

from typing import List, Dict, Optional


def filter_by_view_visibility(
    parts: List[Dict],
    view_name: str,
    side_threshold: float = 5.0
) -> List[Dict]:
    """
    Filter parts based on view visibility.

    Removes:
    1. Parts on the opposite side of the model
    2. Parts enclosed inside other larger parts

    Args:
        parts: List of part dictionaries with bounding box info
        view_name: View angle (Left, Right, Front, etc.)
        side_threshold: Distance threshold for center-line visibility (mm)

    Returns:
        List of visible parts
    """
    # Extract parts with valid bounding boxes
    parts_data = []
    for part in parts:
        bbox = part.get("bounding_box")
        if bbox and part.get("visible", True):
            parts_data.append({
                "name": part["name"],
                "label": part.get("label", part["name"]),
                "bbox": bbox,
                "color": part.get("color")
            })

    # If no bounding boxes available, return all parts
    if not parts_data:
        return [
            {
                "name": p["name"],
                "label": p.get("label", p["name"]),
                "color": p.get("color")
            }
            for p in parts
        ]

    # Calculate model center
    all_x = [(p["bbox"]["min"]["x"] + p["bbox"]["max"]["x"]) / 2 for p in parts_data]
    all_y = [(p["bbox"]["min"]["y"] + p["bbox"]["max"]["y"]) / 2 for p in parts_data]

    model_center_x = sum(all_x) / len(all_x)
    model_center_y = sum(all_y) / len(all_y)

    visible_parts = []

    for part in parts_data:
        bbox = part["bbox"]
        part_center_x = (bbox["min"]["x"] + bbox["max"]["x"]) / 2
        part_center_y = (bbox["min"]["y"] + bbox["max"]["y"]) / 2

        # Check if on opposite side
        is_hidden = _is_on_opposite_side(
            view_name, part_center_x, part_center_y,
            model_center_x, model_center_y, side_threshold
        )

        if is_hidden:
            continue

        # Check if enclosed inside another part (occlusion check)
        is_occluded = _check_occlusion(part, parts_data, view_name)

        if not is_occluded:
            visible_parts.append({
                "name": part["name"],
                "label": part["label"],
                "color": part["color"]
            })

    return visible_parts


def _is_on_opposite_side(
    view_name: str,
    part_center_x: float,
    part_center_y: float,
    model_center_x: float,
    model_center_y: float,
    threshold: float
) -> bool:
    """Check if part is on the opposite side from the view."""
    if view_name in ["Left", "FrontLeft", "RearLeft"]:
        return part_center_x > model_center_x + threshold
    elif view_name in ["Right", "FrontRight", "RearRight"]:
        return part_center_x < model_center_x - threshold
    elif view_name == "Front":
        return part_center_y > model_center_y + threshold
    elif view_name == "Rear":
        return part_center_y < model_center_y - threshold

    return False


def _check_occlusion(
    part: Dict,
    all_parts: List[Dict],
    view_name: str
) -> bool:
    """Check if a part is occluded (inside) another larger part."""
    bbox = part["bbox"]
    part_volume = _calculate_volume(bbox)

    for other in all_parts:
        if other["name"] == part["name"]:
            continue

        other_bbox = other["bbox"]
        other_volume = _calculate_volume(other_bbox)

        # Only check if other part is significantly larger
        if other_volume <= part_volume * 2:
            continue

        if _is_enclosed(bbox, other_bbox, view_name):
            return True

    return False


def _calculate_volume(bbox: Dict) -> float:
    """Calculate volume of a bounding box."""
    return (
        (bbox["max"]["x"] - bbox["min"]["x"]) *
        (bbox["max"]["y"] - bbox["min"]["y"]) *
        (bbox["max"]["z"] - bbox["min"]["z"])
    )


def _is_enclosed(bbox: Dict, other_bbox: Dict, view_name: str) -> bool:
    """Check if bbox is enclosed by other_bbox for a given view."""
    tolerance = 1  # mm

    if view_name in ["Left", "Right", "FrontLeft", "FrontRight", "RearLeft", "RearRight"]:
        y_inside = (
            bbox["min"]["y"] >= other_bbox["min"]["y"] - tolerance and
            bbox["max"]["y"] <= other_bbox["max"]["y"] + tolerance
        )
        z_inside = (
            bbox["min"]["z"] >= other_bbox["min"]["z"] - tolerance and
            bbox["max"]["z"] <= other_bbox["max"]["z"] + tolerance
        )
        x_inside = (
            bbox["min"]["x"] > other_bbox["min"]["x"] and
            bbox["max"]["x"] < other_bbox["max"]["x"]
        )
        return y_inside and z_inside and x_inside

    elif view_name in ["Front", "Rear"]:
        x_inside = (
            bbox["min"]["x"] >= other_bbox["min"]["x"] - tolerance and
            bbox["max"]["x"] <= other_bbox["max"]["x"] + tolerance
        )
        z_inside = (
            bbox["min"]["z"] >= other_bbox["min"]["z"] - tolerance and
            bbox["max"]["z"] <= other_bbox["max"]["z"] + tolerance
        )
        y_inside = (
            bbox["min"]["y"] > other_bbox["min"]["y"] and
            bbox["max"]["y"] < other_bbox["max"]["y"]
        )
        return x_inside and z_inside and y_inside

    elif view_name == "Top":
        x_inside = (
            bbox["min"]["x"] >= other_bbox["min"]["x"] - tolerance and
            bbox["max"]["x"] <= other_bbox["max"]["x"] + tolerance
        )
        y_inside = (
            bbox["min"]["y"] >= other_bbox["min"]["y"] - tolerance and
            bbox["max"]["y"] <= other_bbox["max"]["y"] + tolerance
        )
        z_inside = (
            bbox["min"]["z"] > other_bbox["min"]["z"] and
            bbox["max"]["z"] < other_bbox["max"]["z"]
        )
        return x_inside and y_inside and z_inside

    return False
