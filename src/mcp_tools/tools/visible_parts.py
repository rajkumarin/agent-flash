"""
MCP Tool: get_visible_parts

Get parts visible from a specific view angle with automatic filtering
of hidden/internal parts.
"""

from ..base import BaseMCPTool, ToolResult
from ..visibility import filter_by_view_visibility


class GetVisiblePartsTool(BaseMCPTool):
    """
    Get list of parts visible from a specific view angle.

    This tool filters out:
    1. Parts on the opposite side of the model (not visible from camera)
    2. Internal parts enclosed inside other parts
    """

    name = "get_visible_parts"
    description = (
        "Get list of parts visible from a specific view angle. "
        "Filters out parts on the opposite side and internal/enclosed parts."
    )
    parameters = {
        "doc_name": {
            "type": "string",
            "required": True,
            "description": "FreeCAD document name"
        },
        "view_name": {
            "type": "string",
            "required": True,
            "description": "View angle: Left, Right, Front, Rear, Top, FrontLeft, FrontRight, RearLeft, RearRight"
        },
        "side_threshold": {
            "type": "number",
            "required": False,
            "default": 5.0,
            "description": "Distance threshold for visibility (mm)"
        }
    }

    def execute(
        self,
        doc_name: str,
        view_name: str,
        side_threshold: float = 5.0
    ) -> ToolResult:
        """
        Execute the get_visible_parts tool.

        Args:
            doc_name: Name of the FreeCAD document
            view_name: View angle (Left, Right, Front, Rear, Top, FrontLeft, etc.)
            side_threshold: Distance threshold for center-line visibility (mm)

        Returns:
            ToolResult with list of visible parts and their properties
        """
        try:
            # Get all parts with bounding boxes
            result = self.proxy.get_all_parts_mapping(doc_name)

            if not result.get("success"):
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to get parts mapping")
                )

            all_parts = result.get("parts", [])

            if not all_parts:
                return ToolResult(
                    success=True,
                    data={"visible_parts": [], "total_parts": 0}
                )

            # Filter parts by visibility
            visible_parts = filter_by_view_visibility(
                all_parts, view_name, side_threshold
            )

            # Get hidden parts list
            visible_names = {p["name"] for p in visible_parts}
            hidden_parts = [
                p["label"] for p in all_parts
                if p["name"] not in visible_names
            ]

            return ToolResult(
                success=True,
                data={
                    "view": view_name,
                    "total_parts": len(all_parts),
                    "visible_count": len(visible_parts),
                    "hidden_count": len(all_parts) - len(visible_parts),
                    "visible_parts": visible_parts,
                    "hidden_parts": hidden_parts
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
