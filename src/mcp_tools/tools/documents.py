"""
MCP Tool: list_documents

List all open FreeCAD documents.
"""

from ..base import BaseMCPTool, ToolResult


class ListDocumentsTool(BaseMCPTool):
    """List all open FreeCAD documents."""

    name = "list_documents"
    description = "List all open FreeCAD documents."
    parameters = {}

    def execute(self) -> ToolResult:
        """
        Execute the list_documents tool.

        Returns:
            ToolResult with list of document names
        """
        try:
            docs = self.proxy.list_documents()
            return ToolResult(
                success=True,
                data={
                    "documents": docs,
                    "count": len(docs)
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
