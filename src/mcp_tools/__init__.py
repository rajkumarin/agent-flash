"""
MCP Tools for FreeCAD

This package provides a modular interface for interacting with FreeCAD
through the Model Context Protocol (MCP). Tools are organized by functionality:

- client: Main FreeCADMCPTools class
- tools/: Individual tool implementations
- visibility: View-based visibility filtering
- registry: Tool metadata and discovery
- gemini: Google Gemini AI integration

Usage:
    from mcp_tools import FreeCADMCPTools, ToolResult

    tools = FreeCADMCPTools(host="localhost", port=9875)
    if tools.ping():
        result = tools.list_documents()
        print(result.data)
"""

from .base import ToolResult
from .client import FreeCADMCPTools
from .registry import TOOL_REGISTRY, get_tools_description

__all__ = [
    "FreeCADMCPTools",
    "ToolResult",
    "TOOL_REGISTRY",
    "get_tools_description",
]
