"""Base classes and types for MCP Tools."""

from dataclasses import dataclass
from typing import Any, Optional
from xmlrpc.client import ServerProxy


@dataclass
class ToolResult:
    """Result from an MCP tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error
        }


class BaseMCPTool:
    """Base class for MCP tools."""

    def __init__(self, proxy: ServerProxy):
        """
        Initialize the tool with an XML-RPC proxy.

        Args:
            proxy: ServerProxy connected to FreeCAD
        """
        self.proxy = proxy

    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool.

        Override this method in subclasses.
        """
        raise NotImplementedError("Subclasses must implement execute()")
