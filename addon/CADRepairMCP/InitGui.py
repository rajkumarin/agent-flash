# FreeCAD InitGui.py for CAD Repair MCP Addon
# This file is executed when FreeCAD GUI starts

from PySide import QtGui


class CADRepairMCPWorkbench(Workbench):
    """CAD Repair MCP Workbench for AI-assisted car model repair."""

    MenuText = "CAD Repair Assistant"
    ToolTip = "AI-powered car model repair assistant with MCP communication"
    Icon = ""

    def Initialize(self):
        """Initialize the workbench when first activated."""
        from rpc_server import rpc_server

        commands = ["Start_RPC_Server", "Stop_RPC_Server"]
        self.appendToolbar("CAD Repair MCP", commands)
        self.appendMenu("CAD Repair MCP", commands)

        FreeCAD.Console.PrintMessage("CAD Repair MCP Workbench initialized\n")

    def Activated(self):
        """Called when workbench is activated."""
        FreeCAD.Console.PrintMessage("CAD Repair MCP Workbench activated\n")

    def Deactivated(self):
        """Called when workbench is deactivated."""
        pass

    def ContextMenu(self, recipient):
        """Context menu for the workbench."""
        pass

    def GetClassName(self):
        """Return the C++ class name."""
        return "Gui::PythonWorkbench"


# Register the workbench
Gui.addWorkbench(CADRepairMCPWorkbench())
