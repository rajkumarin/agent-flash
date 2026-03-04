"""Tool Registry for MCP Tools.

Provides metadata about available tools for AI discovery.
"""

from typing import Dict, Any

from .tools import (
    GetVisiblePartsTool,
    GetViewScreenshotTool,
    ListDocumentsTool,
    GetAllPartsTool,
    GetPartDetailsTool,
    HighlightPartTool,
    CompareViewsTool,
)


# Registry of all available tools with their metadata
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "get_visible_parts": {
        "name": GetVisiblePartsTool.name,
        "description": GetVisiblePartsTool.description,
        "parameters": GetVisiblePartsTool.parameters,
        "class": GetVisiblePartsTool,
    },
    "get_view_screenshot": {
        "name": GetViewScreenshotTool.name,
        "description": GetViewScreenshotTool.description,
        "parameters": GetViewScreenshotTool.parameters,
        "class": GetViewScreenshotTool,
    },
    "list_documents": {
        "name": ListDocumentsTool.name,
        "description": ListDocumentsTool.description,
        "parameters": ListDocumentsTool.parameters,
        "class": ListDocumentsTool,
    },
    "get_all_parts": {
        "name": GetAllPartsTool.name,
        "description": GetAllPartsTool.description,
        "parameters": GetAllPartsTool.parameters,
        "class": GetAllPartsTool,
    },
    "get_part_details": {
        "name": GetPartDetailsTool.name,
        "description": GetPartDetailsTool.description,
        "parameters": GetPartDetailsTool.parameters,
        "class": GetPartDetailsTool,
    },
    "highlight_part": {
        "name": HighlightPartTool.name,
        "description": HighlightPartTool.description,
        "parameters": HighlightPartTool.parameters,
        "class": HighlightPartTool,
    },
    "compare_views": {
        "name": CompareViewsTool.name,
        "description": CompareViewsTool.description,
        "parameters": CompareViewsTool.parameters,
        "class": CompareViewsTool,
    },
}


def get_tools_description() -> str:
    """
    Get a formatted description of all available MCP tools for the AI.

    Returns:
        Markdown-formatted string describing all tools
    """
    lines = ["## Available MCP Tools\n"]

    for tool_name, tool_info in TOOL_REGISTRY.items():
        lines.append(f"### {tool_name}")
        lines.append(f"{tool_info['description']}\n")

        if tool_info['parameters']:
            lines.append("**Parameters:**")
            for param_name, param_info in tool_info['parameters'].items():
                req = "required" if param_info.get('required') else "optional"
                default = f", default: {param_info['default']}" if 'default' in param_info else ""
                lines.append(
                    f"- `{param_name}` ({param_info['type']}, {req}{default}): "
                    f"{param_info['description']}"
                )
        lines.append("")

    return "\n".join(lines)


def get_tool_info(tool_name: str) -> Dict[str, Any]:
    """
    Get information about a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Tool metadata dictionary or empty dict if not found
    """
    return TOOL_REGISTRY.get(tool_name, {})


def list_tool_names() -> list:
    """
    Get list of all available tool names.

    Returns:
        List of tool name strings
    """
    return list(TOOL_REGISTRY.keys())
