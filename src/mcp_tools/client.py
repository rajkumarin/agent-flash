"""
FreeCAD MCP Tools Client

Main client class that provides the public API for interacting with FreeCAD
through MCP tools. All tools are instantiated here and exposed through
convenient methods.
"""

from typing import Optional, List
from xmlrpc.client import ServerProxy

from .base import ToolResult
from utils.logger import log
from .tools import (
    GetVisiblePartsTool,
    GetViewScreenshotTool,
    ListDocumentsTool,
    GetAllPartsTool,
    GetPartDetailsTool,
    HighlightPartTool,
    CompareViewsTool,
)


class FreeCADMCPTools:
    """
    Main client for FreeCAD MCP Tools.

    Provides a unified interface to interact with FreeCAD through various
    MCP tools for CAD model analysis and manipulation.

    Usage:
        tools = FreeCADMCPTools(host="localhost", port=9875)
        if tools.ping():
            docs = tools.list_documents()
            parts = tools.get_visible_parts("MyModel", "Left")
    """

    def __init__(self, host: str = "localhost", port: int = 9875):
        """
        Initialize the MCP Tools client.

        Args:
            host: FreeCAD RPC server host
            port: FreeCAD RPC server port
        """
        self.host = host
        self.port = port
        self._proxy: Optional[ServerProxy] = None

        # Tool instances (lazy initialized)
        self._visible_parts_tool: Optional[GetVisiblePartsTool] = None
        self._screenshot_tool: Optional[GetViewScreenshotTool] = None
        self._documents_tool: Optional[ListDocumentsTool] = None
        self._all_parts_tool: Optional[GetAllPartsTool] = None
        self._part_details_tool: Optional[GetPartDetailsTool] = None
        self._highlight_tool: Optional[HighlightPartTool] = None
        self._compare_tool: Optional[CompareViewsTool] = None

    @property
    def proxy(self) -> ServerProxy:
        """Get or create the XML-RPC proxy."""
        if self._proxy is None:
            self._proxy = ServerProxy(
                f"http://{self.host}:{self.port}",
                allow_none=True
            )
        return self._proxy

    def _get_visible_parts_tool(self) -> GetVisiblePartsTool:
        """Get or create the visible parts tool."""
        if self._visible_parts_tool is None:
            self._visible_parts_tool = GetVisiblePartsTool(self.proxy)
        return self._visible_parts_tool

    def _get_screenshot_tool(self) -> GetViewScreenshotTool:
        """Get or create the screenshot tool."""
        if self._screenshot_tool is None:
            self._screenshot_tool = GetViewScreenshotTool(self.proxy)
        return self._screenshot_tool

    def _get_documents_tool(self) -> ListDocumentsTool:
        """Get or create the documents tool."""
        if self._documents_tool is None:
            self._documents_tool = ListDocumentsTool(self.proxy)
        return self._documents_tool

    def _get_all_parts_tool(self) -> GetAllPartsTool:
        """Get or create the all parts tool."""
        if self._all_parts_tool is None:
            self._all_parts_tool = GetAllPartsTool(self.proxy)
        return self._all_parts_tool

    def _get_part_details_tool(self) -> GetPartDetailsTool:
        """Get or create the part details tool."""
        if self._part_details_tool is None:
            self._part_details_tool = GetPartDetailsTool(self.proxy)
        return self._part_details_tool

    def _get_highlight_tool(self) -> HighlightPartTool:
        """Get or create the highlight tool."""
        if self._highlight_tool is None:
            self._highlight_tool = HighlightPartTool(self.proxy)
        return self._highlight_tool

    def _get_compare_tool(self) -> CompareViewsTool:
        """Get or create the compare tool."""
        if self._compare_tool is None:
            self._compare_tool = CompareViewsTool(
                self.proxy,
                self.get_visible_parts
            )
        return self._compare_tool

    # -------------------------------------------------------------------------
    # Connection Methods
    # -------------------------------------------------------------------------

    def ping(self) -> bool:
        """
        Test connection to FreeCAD RPC server.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            result = self.proxy.ping()
            log(f"FreeCAD RPC ping successful: {self.host}:{self.port}", "DEBUG")
            return result
        except Exception as e:
            log(f"FreeCAD RPC ping failed: {self.host}:{self.port} - {e}", "ERROR")
            return False

    def reconnect(self, host: Optional[str] = None, port: Optional[int] = None) -> bool:
        """
        Reconnect to FreeCAD server with optional new host/port.

        Args:
            host: New host (optional)
            port: New port (optional)

        Returns:
            True if reconnection successful
        """
        if host:
            self.host = host
        if port:
            self.port = port

        # Reset proxy and tools
        self._proxy = None
        self._visible_parts_tool = None
        self._screenshot_tool = None
        self._documents_tool = None
        self._all_parts_tool = None
        self._part_details_tool = None
        self._highlight_tool = None
        self._compare_tool = None

        return self.ping()

    # -------------------------------------------------------------------------
    # Document Methods
    # -------------------------------------------------------------------------

    def list_documents(self) -> ToolResult:
        """
        List all open FreeCAD documents.

        Returns:
            ToolResult with list of document names
        """
        return self._get_documents_tool().execute()

    # -------------------------------------------------------------------------
    # Part Methods
    # -------------------------------------------------------------------------

    def get_all_parts(self, doc_name: str) -> ToolResult:
        """
        Get all parts in a document with their metadata.

        Args:
            doc_name: Name of the FreeCAD document

        Returns:
            ToolResult with list of parts
        """
        return self._get_all_parts_tool().execute(doc_name)

    def get_visible_parts(
        self,
        doc_name: str,
        view_name: str = "Left",
        side_threshold: float = 5.0
    ) -> ToolResult:
        """
        Get parts visible from a specific view angle.

        Args:
            doc_name: Name of the FreeCAD document
            view_name: View angle (Left, Right, Front, Rear, Top, etc.)
            side_threshold: Distance threshold for visibility (mm)

        Returns:
            ToolResult with visible parts list
        """
        return self._get_visible_parts_tool().execute(
            doc_name, view_name, side_threshold
        )

    def get_part_details(self, doc_name: str, part_name: str) -> ToolResult:
        """
        Get detailed information about a specific part.

        Args:
            doc_name: Name of the FreeCAD document
            part_name: Name of the part

        Returns:
            ToolResult with part details
        """
        return self._get_part_details_tool().execute(doc_name, part_name)

    def highlight_part(
        self,
        doc_name: str,
        part_name: str,
        color: Optional[List[float]] = None
    ) -> ToolResult:
        """
        Highlight a part with a specific color.

        Args:
            doc_name: Name of the FreeCAD document
            part_name: Name of the part to highlight
            color: RGBA color [r, g, b, a] in 0-1 range

        Returns:
            ToolResult with highlight status
        """
        return self._get_highlight_tool().execute(doc_name, part_name, color)

    # -------------------------------------------------------------------------
    # Screenshot Methods
    # -------------------------------------------------------------------------

    def get_view_screenshot(
        self,
        doc_name: Optional[str] = None,
        view_name: str = "Isometric"
    ) -> ToolResult:
        """
        Capture a screenshot from a specific view angle.

        Args:
            doc_name: Document name (optional, uses active if not specified)
            view_name: View angle (Isometric, Left, Right, Front, etc.)

        Returns:
            ToolResult with base64-encoded image
        """
        return self._get_screenshot_tool().execute(doc_name, view_name)

    # -------------------------------------------------------------------------
    # Comparison Methods
    # -------------------------------------------------------------------------

    def compare_views(
        self,
        doc_name: str,
        view1: str = "Left",
        view2: str = "Right"
    ) -> ToolResult:
        """
        Compare which parts are visible between two views.

        Args:
            doc_name: Name of the FreeCAD document
            view1: First view angle
            view2: Second view angle

        Returns:
            ToolResult with comparison data
        """
        return self._get_compare_tool().execute(doc_name, view1, view2)

    # -------------------------------------------------------------------------
    # Direct Proxy Access (for advanced usage)
    # -------------------------------------------------------------------------

    def get_objects(self, doc_name: str) -> list:
        """
        Get all objects from a document (direct proxy call).

        Args:
            doc_name: Name of the FreeCAD document

        Returns:
            List of object dictionaries
        """
        try:
            return self.proxy.get_objects(doc_name)
        except Exception:
            return []

    def get_model_overview_screenshot(
        self,
        doc_name: str,
        missing_parts: List[str],
        damaged_parts: List[str],
        view_name: str = "Isometric"
    ) -> dict:
        """
        Get screenshot with highlighted parts (direct proxy call).

        Args:
            doc_name: Document name
            missing_parts: List of missing part names to highlight
            damaged_parts: List of damaged part names to highlight
            view_name: View angle

        Returns:
            Dict with success, image, etc.
        """
        try:
            return self.proxy.get_model_overview_screenshot(
                doc_name, missing_parts, damaged_parts, view_name
            )
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_part_isolated_view(
        self,
        doc_name: str,
        part_name: str,
        view_name: str = "Isometric"
    ) -> dict:
        """
        Get isolated view of a single part (direct proxy call).

        Args:
            doc_name: Document name
            part_name: Part to isolate
            view_name: View angle

        Returns:
            Dict with success, image, etc.
        """
        try:
            return self.proxy.get_part_isolated_view(
                doc_name, part_name, view_name
            )
        except Exception as e:
            return {"success": False, "error": str(e)}
