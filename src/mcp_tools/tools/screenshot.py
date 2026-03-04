"""
MCP Tool: get_view_screenshot

Capture a screenshot of the CAD model from a specific view angle.
"""

from typing import Optional

from ..base import BaseMCPTool, ToolResult


class GetViewScreenshotTool(BaseMCPTool):
    """Capture a screenshot from a specific view angle."""

    name = "get_view_screenshot"
    description = "Capture a screenshot of the CAD model from a specific view angle."
    parameters = {
        "doc_name": {
            "type": "string",
            "required": False,
            "description": "Document name (optional, uses active if not specified)"
        },
        "view_name": {
            "type": "string",
            "required": False,
            "default": "Isometric",
            "description": "View angle"
        }
    }

    def execute(
        self,
        doc_name: Optional[str] = None,
        view_name: str = "Isometric"
    ) -> ToolResult:
        """
        Execute the get_view_screenshot tool.

        Args:
            doc_name: Optional document name (uses active if not specified)
            view_name: View angle (Isometric, Left, Right, Front, Rear, Top)

        Returns:
            ToolResult with base64-encoded image
        """
        try:
            if doc_name:
                # Use model overview screenshot with empty highlight lists
                image_result = self.proxy.get_model_overview_screenshot(
                    doc_name, [], [], view_name
                )
                if image_result.get("success"):
                    return ToolResult(
                        success=True,
                        data={
                            "image": image_result.get("image"),
                            "view": view_name,
                            "format": "base64_png"
                        }
                    )
                else:
                    return ToolResult(
                        success=False,
                        error=image_result.get("error")
                    )
            else:
                # Use active document screenshot
                image_b64 = self.proxy.get_active_screenshot(view_name)
                if image_b64:
                    return ToolResult(
                        success=True,
                        data={
                            "image": image_b64,
                            "view": view_name,
                            "format": "base64_png"
                        }
                    )
                return ToolResult(
                    success=False,
                    error="Failed to capture screenshot"
                )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
