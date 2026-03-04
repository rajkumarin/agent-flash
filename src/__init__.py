"""
CAD Repair Assistant

AI-powered assistant for identifying missing or damaged parts in CAD models
by comparing uploaded images against FreeCAD reference models.

Modules:
    - config: Configuration constants
    - mcp_tools: FreeCAD MCP Tools interface
    - utils: Utility functions (logging, color, image)
    - core: Core functionality (analysis, rendering, model context)
    - ui: Streamlit UI components
"""

__version__ = "1.0.0"
__author__ = "CAD Repair Assistant Team"

from config import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    VIEW_ANGLES,
    GEMINI_MODEL,
)

from mcp_tools import FreeCADMCPTools, ToolResult

__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "VIEW_ANGLES",
    "GEMINI_MODEL",
    "FreeCADMCPTools",
    "ToolResult",
]
