"""
MCP Tool: compare_views

Compare which parts are visible between two different view angles.
"""

from ..base import BaseMCPTool, ToolResult


class CompareViewsTool(BaseMCPTool):
    """Compare which parts are visible between two views."""

    name = "compare_views"
    description = "Compare which parts are visible between two different view angles."
    parameters = {
        "doc_name": {
            "type": "string",
            "required": True,
            "description": "FreeCAD document name"
        },
        "view1": {
            "type": "string",
            "required": True,
            "description": "First view angle"
        },
        "view2": {
            "type": "string",
            "required": True,
            "description": "Second view angle"
        }
    }

    def __init__(self, proxy, get_visible_parts_func):
        """
        Initialize the compare tool.

        Args:
            proxy: ServerProxy connected to FreeCAD
            get_visible_parts_func: Function to get visible parts (from client)
        """
        super().__init__(proxy)
        self._get_visible_parts = get_visible_parts_func

    def execute(self, doc_name: str, view1: str, view2: str) -> ToolResult:
        """
        Execute the compare_views tool.

        Args:
            doc_name: Name of the FreeCAD document
            view1: First view angle
            view2: Second view angle

        Returns:
            ToolResult with comparison data (parts in both, only view1, only view2)
        """
        try:
            result1 = self._get_visible_parts(doc_name, view1)
            result2 = self._get_visible_parts(doc_name, view2)

            if not result1.success:
                return result1
            if not result2.success:
                return result2

            parts1 = {p["name"] for p in result1.data["visible_parts"]}
            parts2 = {p["name"] for p in result2.data["visible_parts"]}

            in_both = parts1 & parts2
            only_view1 = parts1 - parts2
            only_view2 = parts2 - parts1

            return ToolResult(
                success=True,
                data={
                    "view1": view1,
                    "view2": view2,
                    "parts_in_both": list(in_both),
                    "parts_only_in_view1": list(only_view1),
                    "parts_only_in_view2": list(only_view2),
                    "view1_total": len(parts1),
                    "view2_total": len(parts2),
                    "overlap_count": len(in_both)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
