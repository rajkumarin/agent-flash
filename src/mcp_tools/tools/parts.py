"""
MCP Tools for part operations:
- get_all_parts: Get all parts in a document
- get_part_details: Get detailed information about a specific part
- highlight_part: Highlight a specific part with a color
"""

from typing import Optional, List

from ..base import BaseMCPTool, ToolResult


class GetAllPartsTool(BaseMCPTool):
    """Get all parts in a document with full metadata."""

    name = "get_all_parts"
    description = "Get all parts in a document with their metadata (name, label, type, color)."
    parameters = {
        "doc_name": {
            "type": "string",
            "required": True,
            "description": "FreeCAD document name"
        }
    }

    def execute(self, doc_name: str) -> ToolResult:
        """
        Execute the get_all_parts tool.

        Args:
            doc_name: Name of the FreeCAD document

        Returns:
            ToolResult with list of all parts and their properties
        """
        try:
            objects = self.proxy.get_objects(doc_name)

            parts = []
            for obj in objects:
                part_info = {
                    "name": obj.get("Name"),
                    "label": obj.get("Label"),
                    "type": obj.get("TypeId"),
                }

                # Extract color if available
                view_obj = obj.get("ViewObject", {})
                if "ShapeColor" in view_obj:
                    color = view_obj["ShapeColor"]
                    part_info["color"] = {
                        "r": color[0] if len(color) > 0 else 0,
                        "g": color[1] if len(color) > 1 else 0,
                        "b": color[2] if len(color) > 2 else 0,
                    }

                parts.append(part_info)

            return ToolResult(
                success=True,
                data={
                    "document": doc_name,
                    "parts": parts,
                    "count": len(parts)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetPartDetailsTool(BaseMCPTool):
    """Get detailed information about a specific part."""

    name = "get_part_details"
    description = "Get detailed information about a specific part including bounding box."
    parameters = {
        "doc_name": {
            "type": "string",
            "required": True,
            "description": "FreeCAD document name"
        },
        "part_name": {
            "type": "string",
            "required": True,
            "description": "Name of the part"
        }
    }

    def execute(self, doc_name: str, part_name: str) -> ToolResult:
        """
        Execute the get_part_details tool.

        Args:
            doc_name: Name of the FreeCAD document
            part_name: Name of the part to inspect

        Returns:
            ToolResult with part details including bounding box
        """
        try:
            # Get part object
            obj = self.proxy.get_object(doc_name, part_name)
            if not obj:
                return ToolResult(
                    success=False,
                    error=f"Part '{part_name}' not found in '{doc_name}'"
                )

            # Get bounding box
            bbox_result = self.proxy.get_part_bounding_box(doc_name, part_name)

            part_info = {
                "name": obj.get("Name"),
                "label": obj.get("Label"),
                "type": obj.get("TypeId"),
                "bounding_box": bbox_result.get("bounding_box") if bbox_result.get("success") else None
            }

            # Extract color
            view_obj = obj.get("ViewObject", {})
            if "ShapeColor" in view_obj:
                color = view_obj["ShapeColor"]
                part_info["color"] = {
                    "r": color[0] if len(color) > 0 else 0,
                    "g": color[1] if len(color) > 1 else 0,
                    "b": color[2] if len(color) > 2 else 0,
                }

            return ToolResult(success=True, data=part_info)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HighlightPartTool(BaseMCPTool):
    """Highlight a specific part with a color."""

    name = "highlight_part"
    description = "Highlight a specific part with a color in the FreeCAD view."
    parameters = {
        "doc_name": {
            "type": "string",
            "required": True,
            "description": "FreeCAD document name"
        },
        "part_name": {
            "type": "string",
            "required": True,
            "description": "Name of the part to highlight"
        },
        "color": {
            "type": "array",
            "required": False,
            "description": "RGBA color [r,g,b,a] 0-1 range"
        }
    }

    # Default highlight color (orange)
    DEFAULT_COLOR = [1.0, 0.5, 0.0, 1.0]

    def execute(
        self,
        doc_name: str,
        part_name: str,
        color: Optional[List[float]] = None
    ) -> ToolResult:
        """
        Execute the highlight_part tool.

        Args:
            doc_name: Name of the FreeCAD document
            part_name: Name of the part to highlight
            color: RGBA color [r, g, b, a] (0-1 range). Default: orange

        Returns:
            ToolResult with highlight status
        """
        try:
            if color is None:
                color = self.DEFAULT_COLOR

            result = self.proxy.highlight_part(doc_name, part_name, color)

            if result.get("success"):
                return ToolResult(
                    success=True,
                    data={
                        "part": part_name,
                        "color": color,
                        "original_color": result.get("original_color")
                    }
                )
            return ToolResult(success=False, error=result.get("error"))

        except Exception as e:
            return ToolResult(success=False, error=str(e))
