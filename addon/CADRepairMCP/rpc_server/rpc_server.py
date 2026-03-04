"""
RPC Server for CAD Repair MCP.

This module provides an XML-RPC server that runs inside FreeCAD,
allowing external applications (like the MCP server) to control FreeCAD
and analyze 3D models.
"""

import FreeCAD
import FreeCADGui
import ObjectsFem

import contextlib
import queue
import base64
import io
import os
import tempfile
import threading
from dataclasses import dataclass, field
from typing import Any
from xmlrpc.server import SimpleXMLRPCServer

from PySide import QtCore

from .parts_library import get_parts_list, insert_part_from_library
from .serialize import serialize_object

# Global server references
rpc_server_thread = None
rpc_server_instance = None

# GUI task queue for thread-safe FreeCAD operations
rpc_request_queue = queue.Queue()
rpc_response_queue = queue.Queue()


def process_gui_tasks():
    """Process tasks in the GUI thread. Called periodically via QTimer."""
    while not rpc_request_queue.empty():
        task = rpc_request_queue.get()
        res = task()
        if res is not None:
            rpc_response_queue.put(res)
    QtCore.QTimer.singleShot(500, process_gui_tasks)


@dataclass
class Object:
    """Represents a FreeCAD object for creation/modification."""
    name: str
    type: str | None = None
    analysis: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)


def set_object_property(
    doc: FreeCAD.Document, obj: FreeCAD.DocumentObject, properties: dict[str, Any]
):
    """Set properties on a FreeCAD object."""
    for prop, val in properties.items():
        try:
            if prop in obj.PropertiesList:
                if prop == "Placement" and isinstance(val, dict):
                    # Handle placement specially
                    if "Base" in val:
                        pos = val["Base"]
                    elif "Position" in val:
                        pos = val["Position"]
                    else:
                        pos = {}
                    rot = val.get("Rotation", {})
                    placement = FreeCAD.Placement(
                        FreeCAD.Vector(
                            pos.get("x", 0),
                            pos.get("y", 0),
                            pos.get("z", 0),
                        ),
                        FreeCAD.Rotation(
                            FreeCAD.Vector(
                                rot.get("Axis", {}).get("x", 0),
                                rot.get("Axis", {}).get("y", 0),
                                rot.get("Axis", {}).get("z", 1),
                            ),
                            rot.get("Angle", 0),
                        ),
                    )
                    setattr(obj, prop, placement)

                elif isinstance(getattr(obj, prop), FreeCAD.Vector) and isinstance(val, dict):
                    vector = FreeCAD.Vector(
                        val.get("x", 0), val.get("y", 0), val.get("z", 0)
                    )
                    setattr(obj, prop, vector)

                elif prop in ["Base", "Tool", "Source", "Profile"] and isinstance(val, str):
                    ref_obj = doc.getObject(val)
                    if ref_obj:
                        setattr(obj, prop, ref_obj)
                    else:
                        raise ValueError(f"Referenced object '{val}' not found.")

                elif prop == "References" and isinstance(val, list):
                    refs = []
                    for ref_name, face in val:
                        ref_obj = doc.getObject(ref_name)
                        if ref_obj:
                            refs.append((ref_obj, face))
                        else:
                            raise ValueError(f"Referenced object '{ref_name}' not found.")
                    setattr(obj, prop, refs)

                else:
                    setattr(obj, prop, val)

            # Handle ViewObject properties
            elif prop == "ShapeColor" and isinstance(val, (list, tuple)):
                setattr(obj.ViewObject, prop, (float(val[0]), float(val[1]), float(val[2]), float(val[3])))

            elif prop == "ViewObject" and isinstance(val, dict):
                for k, v in val.items():
                    if k == "ShapeColor":
                        setattr(obj.ViewObject, k, (float(v[0]), float(v[1]), float(v[2]), float(v[3])))
                    else:
                        setattr(obj.ViewObject, k, v)

            else:
                setattr(obj, prop, val)

        except Exception as e:
            FreeCAD.Console.PrintError(f"Property '{prop}' assignment error: {e}\n")


class FreeCADRPC:
    """RPC server methods for FreeCAD control."""

    def ping(self):
        """Check if server is responsive."""
        return True

    def create_document(self, name="New_Document"):
        """Create a new FreeCAD document."""
        rpc_request_queue.put(lambda: self._create_document_gui(name))
        res = rpc_response_queue.get()
        if res is True:
            return {"success": True, "document_name": name}
        else:
            return {"success": False, "error": res}

    def create_object(self, doc_name, obj_data: dict[str, Any]):
        """Create a new object in a document."""
        obj = Object(
            name=obj_data.get("Name", "New_Object"),
            type=obj_data["Type"],
            analysis=obj_data.get("Analysis", None),
            properties=obj_data.get("Properties", {}),
        )
        rpc_request_queue.put(lambda: self._create_object_gui(doc_name, obj))
        res = rpc_response_queue.get()
        if res is True:
            return {"success": True, "object_name": obj.name}
        else:
            return {"success": False, "error": res}

    def edit_object(self, doc_name: str, obj_name: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Edit an existing object's properties."""
        obj = Object(
            name=obj_name,
            properties=properties.get("Properties", {}),
        )
        rpc_request_queue.put(lambda: self._edit_object_gui(doc_name, obj))
        res = rpc_response_queue.get()
        if res is True:
            return {"success": True, "object_name": obj.name}
        else:
            return {"success": False, "error": res}

    def delete_object(self, doc_name: str, obj_name: str):
        """Delete an object from a document."""
        rpc_request_queue.put(lambda: self._delete_object_gui(doc_name, obj_name))
        res = rpc_response_queue.get()
        if res is True:
            return {"success": True, "object_name": obj_name}
        else:
            return {"success": False, "error": res}

    def execute_code(self, code: str) -> dict[str, Any]:
        """Execute Python code in FreeCAD."""
        output_buffer = io.StringIO()

        def task():
            try:
                with contextlib.redirect_stdout(output_buffer):
                    exec(code, globals())
                FreeCAD.Console.PrintMessage("Python code executed successfully.\n")
                return True
            except Exception as e:
                FreeCAD.Console.PrintError(f"Error executing Python code: {e}\n")
                return f"Error executing Python code: {e}\n"

        rpc_request_queue.put(task)
        res = rpc_response_queue.get()
        if res is True:
            return {
                "success": True,
                "message": "Python code execution scheduled. \nOutput: " + output_buffer.getvalue()
            }
        else:
            return {"success": False, "error": res}

    def get_objects(self, doc_name):
        """Get all objects in a document."""
        doc = FreeCAD.getDocument(doc_name)
        if doc:
            return [serialize_object(obj) for obj in doc.Objects]
        else:
            return []

    def get_object(self, doc_name, obj_name):
        """Get details of a specific object."""
        doc = FreeCAD.getDocument(doc_name)
        if doc:
            obj = doc.getObject(obj_name)
            if obj:
                return serialize_object(obj)
        return None

    def insert_part_from_library(self, relative_path):
        """Insert a part from the parts library."""
        rpc_request_queue.put(lambda: self._insert_part_from_library(relative_path))
        res = rpc_response_queue.get()
        if res is True:
            return {"success": True, "message": "Part inserted from library."}
        else:
            return {"success": False, "error": res}

    def list_documents(self):
        """List all open documents."""
        return list(FreeCAD.listDocuments().keys())

    def get_parts_list(self):
        """Get list of available parts from library."""
        return get_parts_list()

    def highlight_part(self, doc_name: str, part_name: str, color: list = None) -> dict:
        """Highlight a specific part by changing its color.

        Args:
            doc_name: Name of the document
            part_name: Name of the part to highlight
            color: RGBA color list [r, g, b, a] with values 0-1. Default is red [1, 0, 0, 1]

        Returns:
            dict with success status and original color for restoration
        """
        if color is None:
            color = [1.0, 0.0, 0.0, 1.0]  # Default red highlight

        def task():
            try:
                doc = FreeCAD.getDocument(doc_name)
                if not doc:
                    return {"success": False, "error": f"Document '{doc_name}' not found"}

                obj = doc.getObject(part_name)
                if not obj:
                    return {"success": False, "error": f"Part '{part_name}' not found"}

                if not hasattr(obj, "ViewObject") or obj.ViewObject is None:
                    return {"success": False, "error": f"Part '{part_name}' has no ViewObject"}

                # Store original color
                original_color = None
                if hasattr(obj.ViewObject, "ShapeColor"):
                    original_color = list(obj.ViewObject.ShapeColor)

                # Set highlight color
                obj.ViewObject.ShapeColor = tuple(float(c) for c in color)

                return {
                    "success": True,
                    "part_name": part_name,
                    "original_color": original_color,
                    "highlight_color": color
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        rpc_request_queue.put(task)
        return rpc_response_queue.get()

    def reset_part_color(self, doc_name: str, part_name: str, color: list = None) -> dict:
        """Reset a part's color to specified or default color.

        Args:
            doc_name: Name of the document
            part_name: Name of the part
            color: RGBA color list [r, g, b, a]. Default is gray [0.8, 0.8, 0.8, 1.0]

        Returns:
            dict with success status
        """
        if color is None:
            color = [0.8, 0.8, 0.8, 1.0]  # Default gray

        def task():
            try:
                doc = FreeCAD.getDocument(doc_name)
                if not doc:
                    return {"success": False, "error": f"Document '{doc_name}' not found"}

                obj = doc.getObject(part_name)
                if not obj:
                    return {"success": False, "error": f"Part '{part_name}' not found"}

                if not hasattr(obj, "ViewObject") or obj.ViewObject is None:
                    return {"success": False, "error": f"Part '{part_name}' has no ViewObject"}

                obj.ViewObject.ShapeColor = tuple(float(c) for c in color)

                return {"success": True, "part_name": part_name, "color": color}
            except Exception as e:
                return {"success": False, "error": str(e)}

        rpc_request_queue.put(task)
        return rpc_response_queue.get()

    def get_part_bounding_box(self, doc_name: str, part_name: str) -> dict:
        """Get the bounding box of a part for 2D mapping.

        Args:
            doc_name: Name of the document
            part_name: Name of the part

        Returns:
            dict with bounding box coordinates (min/max x, y, z) and center
        """
        def task():
            try:
                doc = FreeCAD.getDocument(doc_name)
                if not doc:
                    return {"success": False, "error": f"Document '{doc_name}' not found"}

                obj = doc.getObject(part_name)
                if not obj:
                    return {"success": False, "error": f"Part '{part_name}' not found"}

                if not hasattr(obj, "Shape") or obj.Shape is None:
                    return {"success": False, "error": f"Part '{part_name}' has no Shape"}

                bbox = obj.Shape.BoundBox

                return {
                    "success": True,
                    "part_name": part_name,
                    "bounding_box": {
                        "min": {"x": bbox.XMin, "y": bbox.YMin, "z": bbox.ZMin},
                        "max": {"x": bbox.XMax, "y": bbox.YMax, "z": bbox.ZMax},
                        "center": {"x": bbox.Center.x, "y": bbox.Center.y, "z": bbox.Center.z},
                        "size": {
                            "x": bbox.XLength,
                            "y": bbox.YLength,
                            "z": bbox.ZLength
                        }
                    }
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        rpc_request_queue.put(task)
        return rpc_response_queue.get()

    def get_all_parts_mapping(self, doc_name: str) -> dict:
        """Get mapping of all parts with their labels, types, and bounding boxes.

        Args:
            doc_name: Name of the document

        Returns:
            dict with list of parts and their metadata for 2D annotation
        """
        def task():
            try:
                doc = FreeCAD.getDocument(doc_name)
                if not doc:
                    return {"success": False, "error": f"Document '{doc_name}' not found"}

                parts = []
                for obj in doc.Objects:
                    part_info = {
                        "name": obj.Name,
                        "label": obj.Label,
                        "type": obj.TypeId,
                        "visible": False,
                        "bounding_box": None,
                        "color": None
                    }

                    # Check visibility
                    if hasattr(obj, "ViewObject") and obj.ViewObject:
                        part_info["visible"] = obj.ViewObject.Visibility
                        if hasattr(obj.ViewObject, "ShapeColor"):
                            part_info["color"] = list(obj.ViewObject.ShapeColor)

                    # Get bounding box if shape exists
                    if hasattr(obj, "Shape") and obj.Shape:
                        try:
                            bbox = obj.Shape.BoundBox
                            part_info["bounding_box"] = {
                                "min": {"x": bbox.XMin, "y": bbox.YMin, "z": bbox.ZMin},
                                "max": {"x": bbox.XMax, "y": bbox.YMax, "z": bbox.ZMax},
                                "center": {"x": bbox.Center.x, "y": bbox.Center.y, "z": bbox.Center.z}
                            }
                        except Exception:
                            pass

                    parts.append(part_info)

                return {
                    "success": True,
                    "document": doc_name,
                    "parts_count": len(parts),
                    "parts": parts
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        rpc_request_queue.put(task)
        return rpc_response_queue.get()

    def get_part_screenshot(
        self,
        doc_name: str,
        part_name: str,
        view_name: str = "Isometric",
        highlight_color: list = None,
        isolate_part: bool = False,
        zoom_to_part: bool = True
    ) -> dict:
        """Get a screenshot focused on a specific part with optional highlighting.

        Args:
            doc_name: Name of the document
            part_name: Name of the part to focus on
            view_name: View angle (Isometric, Front, Top, Right, etc.)
            highlight_color: RGBA color for highlighting [r, g, b, a]. Default red.
            isolate_part: If True, hide all other parts temporarily
            zoom_to_part: If True, zoom/fit view to the part

        Returns:
            dict with base64 screenshot, part info, and success status
        """
        if highlight_color is None:
            highlight_color = [1.0, 0.0, 0.0, 1.0]  # Red

        # Create temp file path before the task
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)

        def do_everything():
            """Do all operations in a single GUI task to avoid race conditions."""
            import time
            original_states = {}

            try:
                doc = FreeCAD.getDocument(doc_name)
                if not doc:
                    return {"success": False, "error": f"Document '{doc_name}' not found"}

                target_obj = doc.getObject(part_name)
                if not target_obj:
                    return {"success": False, "error": f"Part '{part_name}' not found"}

                # Store original states
                for obj in doc.Objects:
                    if hasattr(obj, "ViewObject") and obj.ViewObject:
                        original_states[obj.Name] = {
                            "visibility": obj.ViewObject.Visibility,
                            "color": list(obj.ViewObject.ShapeColor) if hasattr(obj.ViewObject, "ShapeColor") else None
                        }

                # Apply highlighting (but don't isolate - keep all parts visible)
                if hasattr(target_obj, "ViewObject") and target_obj.ViewObject:
                    if hasattr(target_obj.ViewObject, "ShapeColor"):
                        target_obj.ViewObject.ShapeColor = tuple(float(c) for c in highlight_color)
                    target_obj.ViewObject.Visibility = True

                # Only hide other parts if explicitly requested AND isolate_part is True
                if isolate_part:
                    for obj in doc.Objects:
                        if obj.Name != part_name and hasattr(obj, "ViewObject") and obj.ViewObject:
                            obj.ViewObject.Visibility = False

                # Set view - use try/except for each view method
                view = FreeCADGui.ActiveDocument.ActiveView

                # Set the requested view using FreeCAD's built-in view methods
                try:
                    camera = view.getCameraNode()
                    from pivy import coin

                    FreeCAD.Console.PrintMessage(f"[get_part_screenshot] Requested view: {view_name}\n")

                    # Use FreeCAD's built-in view methods
                    if view_name == "Isometric":
                        view.viewIsometric()
                    elif view_name == "Front":
                        view.viewFront()
                    elif view_name == "Rear" or view_name == "Back":
                        view.viewRear()
                    elif view_name == "Top":
                        view.viewTop()
                    elif view_name == "Bottom":
                        view.viewBottom()
                    elif view_name == "Left":
                        view.viewLeft()
                    elif view_name == "Right":
                        view.viewRight()
                    elif view_name in ["FrontLeft", "FrontRight", "RearLeft", "RearRight"]:
                        # Diagonal views need quaternions as FreeCAD doesn't have built-in methods
                        VIEW_QUATERNIONS = {
                            "FrontLeft": (0.17591989, 0.42470819, 0.33985114, 0.82091778),
                            "FrontRight": (0.17591989, -0.42470819, -0.33985114, 0.82091778),
                            "RearLeft": (-0.33985114, 0.82091778, 0.17591989, 0.42470819),
                            "RearRight": (-0.33985114, -0.82091778, -0.17591989, 0.42470819),
                        }
                        quat = VIEW_QUATERNIONS[view_name]
                        rot = coin.SbRotation()
                        rot.setValue(quat[0], quat[1], quat[2], quat[3])
                        camera.orientation.setValue(rot)
                    else:
                        view.viewIsometric()

                    # Save orientation before fitAll/viewSelection (they can reset it)
                    current_rot = camera.orientation.getValue()
                    saved_quat = current_rot.getValue()

                except Exception as view_err:
                    FreeCAD.Console.PrintWarning(f"Could not set view {view_name}: {view_err}\n")
                    saved_quat = None
                    try:
                        view.viewIsometric()
                    except:
                        pass

                # Zoom to part or fit all
                if zoom_to_part and hasattr(target_obj, "Shape") and target_obj.Shape:
                    FreeCADGui.Selection.clearSelection()
                    FreeCADGui.Selection.addSelection(target_obj)
                    view.viewSelection()
                    FreeCADGui.Selection.clearSelection()
                else:
                    view.fitAll()

                # Restore saved orientation after zoom/fit operations
                if saved_quat is not None:
                    try:
                        from pivy import coin
                        restore_rot = coin.SbRotation()
                        restore_rot.setValue(saved_quat[0], saved_quat[1], saved_quat[2], saved_quat[3])
                        camera.orientation.setValue(restore_rot)
                        FreeCAD.Console.PrintMessage(f"[get_part_screenshot] Restored orientation: {saved_quat}\n")
                    except Exception as restore_err:
                        FreeCAD.Console.PrintWarning(f"Could not restore orientation: {restore_err}\n")

                # Force SHADED display mode (not wireframe)
                try:
                    for obj in doc.Objects:
                        if hasattr(obj, "ViewObject") and obj.ViewObject:
                            vo = obj.ViewObject
                            # Try different display mode names
                            if hasattr(vo, "DisplayMode"):
                                for mode in ["Shaded", "Flat Lines", "As Is"]:
                                    try:
                                        vo.DisplayMode = mode
                                        break
                                    except:
                                        continue
                            # Also set DrawStyle if available
                            if hasattr(vo, "DrawStyle"):
                                try:
                                    vo.DrawStyle = "Solid"
                                except:
                                    pass
                except Exception as display_err:
                    FreeCAD.Console.PrintWarning(f"Could not set display mode: {display_err}\n")

                # Force GUI update and wait for rendering
                FreeCADGui.updateGui()
                time.sleep(0.5)

                # Take screenshot - use "Current" to preserve the view's appearance
                view.saveImage(tmp_path, 1920, 1080, "Current")

                # Get part info before restoring
                part_info = {
                    "name": target_obj.Name,
                    "label": target_obj.Label,
                    "type": target_obj.TypeId,
                }
                if hasattr(target_obj, "Shape") and target_obj.Shape:
                    bbox = target_obj.Shape.BoundBox
                    part_info["bounding_box"] = {
                        "center": {"x": bbox.Center.x, "y": bbox.Center.y, "z": bbox.Center.z},
                        "size": {"x": bbox.XLength, "y": bbox.YLength, "z": bbox.ZLength}
                    }

                # Restore original states
                for obj_name, state in original_states.items():
                    obj = doc.getObject(obj_name)
                    if obj and hasattr(obj, "ViewObject") and obj.ViewObject:
                        obj.ViewObject.Visibility = state["visibility"]
                        if state["color"] and hasattr(obj.ViewObject, "ShapeColor"):
                            obj.ViewObject.ShapeColor = tuple(state["color"])

                FreeCADGui.updateGui()

                return {"success": True, "part_info": part_info}

            except Exception as e:
                # Try to restore on error
                try:
                    doc = FreeCAD.getDocument(doc_name)
                    if doc:
                        for obj_name, state in original_states.items():
                            obj = doc.getObject(obj_name)
                            if obj and hasattr(obj, "ViewObject") and obj.ViewObject:
                                obj.ViewObject.Visibility = state["visibility"]
                                if state["color"] and hasattr(obj.ViewObject, "ShapeColor"):
                                    obj.ViewObject.ShapeColor = tuple(state["color"])
                except:
                    pass
                return {"success": False, "error": str(e)}

        # Run everything in a single GUI task
        rpc_request_queue.put(do_everything)
        result = rpc_response_queue.get()

        if result.get("success"):
            try:
                with open(tmp_path, "rb") as f:
                    image_bytes = f.read()
                encoded = base64.b64encode(image_bytes).decode("utf-8")

                return {
                    "success": True,
                    "image": encoded,
                    "part": result.get("part_info"),
                    "view": view_name
                }
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        else:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return result

    def get_model_overview_screenshot(
        self,
        doc_name: str,
        highlight_parts: list = None,
        missing_parts: list = None,
        view_name: str = "Isometric"
    ) -> dict:
        """Get a screenshot of the entire model with optional highlighting of specific parts.

        Args:
            doc_name: Name of the document
            highlight_parts: List of part names to highlight in green (present)
            missing_parts: List of part names to highlight in red (missing/to fix)
            view_name: View angle

        Returns:
            dict with base64 screenshot and success status
        """
        if highlight_parts is None:
            highlight_parts = []
        if missing_parts is None:
            missing_parts = []

        # Create temp file path before the task
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)

        def do_everything():
            """Do all operations in a single GUI task to avoid race conditions."""
            import time
            original_colors = {}

            try:
                doc = FreeCAD.getDocument(doc_name)
                if not doc:
                    return {"success": False, "error": f"Document '{doc_name}' not found"}

                # Store original colors and apply highlights
                for obj in doc.Objects:
                    if hasattr(obj, "ViewObject") and obj.ViewObject and hasattr(obj.ViewObject, "ShapeColor"):
                        original_colors[obj.Name] = list(obj.ViewObject.ShapeColor)

                        if obj.Name in missing_parts or obj.Label in missing_parts:
                            # Red for missing/damaged
                            obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0, 1.0)
                        elif obj.Name in highlight_parts or obj.Label in highlight_parts:
                            # Green for highlighted/present
                            obj.ViewObject.ShapeColor = (0.0, 0.8, 0.0, 1.0)

                # Set view - use try/except for each view method
                view = FreeCADGui.ActiveDocument.ActiveView

                # Set the requested view using FreeCAD's built-in view methods
                try:
                    camera = view.getCameraNode()
                    from pivy import coin

                    FreeCAD.Console.PrintMessage(f"[get_model_overview] Requested view: {view_name}\n")

                    # Use FreeCAD's built-in view methods
                    if view_name == "Isometric":
                        view.viewIsometric()
                    elif view_name == "Front":
                        view.viewFront()
                    elif view_name == "Rear" or view_name == "Back":
                        view.viewRear()
                    elif view_name == "Top":
                        view.viewTop()
                    elif view_name == "Bottom":
                        view.viewBottom()
                    elif view_name == "Left":
                        view.viewLeft()
                    elif view_name == "Right":
                        view.viewRight()
                    elif view_name in ["FrontLeft", "FrontRight", "RearLeft", "RearRight"]:
                        # Diagonal views need quaternions as FreeCAD doesn't have built-in methods
                        VIEW_QUATERNIONS = {
                            "FrontLeft": (0.17591989, 0.42470819, 0.33985114, 0.82091778),
                            "FrontRight": (0.17591989, -0.42470819, -0.33985114, 0.82091778),
                            "RearLeft": (-0.33985114, 0.82091778, 0.17591989, 0.42470819),
                            "RearRight": (-0.33985114, -0.82091778, -0.17591989, 0.42470819),
                        }
                        quat = VIEW_QUATERNIONS[view_name]
                        rot = coin.SbRotation()
                        rot.setValue(quat[0], quat[1], quat[2], quat[3])
                        camera.orientation.setValue(rot)
                    else:
                        view.viewIsometric()

                    # Save orientation before fitAll (fitAll can reset it)
                    current_rot = camera.orientation.getValue()
                    saved_quat = current_rot.getValue()

                    view.fitAll()

                    # Restore orientation after fitAll
                    restore_rot = coin.SbRotation()
                    restore_rot.setValue(saved_quat[0], saved_quat[1], saved_quat[2], saved_quat[3])
                    camera.orientation.setValue(restore_rot)

                except Exception as view_err:
                    FreeCAD.Console.PrintWarning(f"Could not set view {view_name}: {view_err}\n")
                    # Fallback to basic isometric
                    try:
                        view.viewIsometric()
                        view.fitAll()
                    except:
                        pass

                # Force SHADED display mode (not wireframe)
                try:
                    for obj in doc.Objects:
                        if hasattr(obj, "ViewObject") and obj.ViewObject:
                            vo = obj.ViewObject
                            # Try different display mode names
                            if hasattr(vo, "DisplayMode"):
                                for mode in ["Shaded", "Flat Lines", "As Is"]:
                                    try:
                                        vo.DisplayMode = mode
                                        break
                                    except:
                                        continue
                            # Also set DrawStyle if available
                            if hasattr(vo, "DrawStyle"):
                                try:
                                    vo.DrawStyle = "Solid"
                                except:
                                    pass
                except Exception as display_err:
                    FreeCAD.Console.PrintWarning(f"Could not set display mode: {display_err}\n")

                # Force GUI update and wait for rendering
                FreeCADGui.updateGui()
                time.sleep(0.5)

                # Take screenshot - use "Current" to preserve the view's appearance
                view.saveImage(tmp_path, 1920, 1080, "Current")

                # Restore original colors
                for obj_name, color in original_colors.items():
                    obj = doc.getObject(obj_name)
                    if obj and hasattr(obj, "ViewObject") and obj.ViewObject:
                        obj.ViewObject.ShapeColor = tuple(color)

                FreeCADGui.updateGui()

                return {"success": True}

            except Exception as e:
                # Try to restore on error
                try:
                    doc = FreeCAD.getDocument(doc_name)
                    if doc:
                        for obj_name, color in original_colors.items():
                            obj = doc.getObject(obj_name)
                            if obj and hasattr(obj, "ViewObject") and obj.ViewObject:
                                obj.ViewObject.ShapeColor = tuple(color)
                except:
                    pass
                return {"success": False, "error": str(e)}

        # Run everything in a single GUI task
        rpc_request_queue.put(do_everything)
        result = rpc_response_queue.get()

        if result.get("success"):
            try:
                with open(tmp_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                return {
                    "success": True,
                    "image": encoded,
                    "view": view_name,
                    "highlighted": highlight_parts,
                    "missing": missing_parts
                }
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        else:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return result

    def get_active_screenshot(self, view_name: str = "Isometric") -> str:
        """Get a screenshot of the active view.

        Returns a base64-encoded string or None if unavailable.
        """
        def check_view_supports_screenshots():
            try:
                active_view = FreeCADGui.ActiveDocument.ActiveView
                if active_view is None:
                    FreeCAD.Console.PrintWarning("No active view available\n")
                    return False

                view_type = type(active_view).__name__
                has_save_image = hasattr(active_view, 'saveImage')
                FreeCAD.Console.PrintMessage(f"View type: {view_type}, Has saveImage: {has_save_image}\n")
                return has_save_image
            except Exception as e:
                FreeCAD.Console.PrintError(f"Error checking view capabilities: {e}\n")
                return False

        rpc_request_queue.put(check_view_supports_screenshots)
        supports_screenshots = rpc_response_queue.get()

        if not supports_screenshots:
            FreeCAD.Console.PrintWarning("Current view does not support screenshots\n")
            return None

        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        rpc_request_queue.put(lambda: self._save_active_screenshot(tmp_path, view_name))
        res = rpc_response_queue.get()

        if res is True:
            try:
                with open(tmp_path, "rb") as image_file:
                    image_bytes = image_file.read()
                encoded = base64.b64encode(image_bytes).decode("utf-8")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            return encoded
        else:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            FreeCAD.Console.PrintWarning(f"Failed to capture screenshot: {res}\n")
            return None

    # Internal GUI methods (run in main thread)

    def _create_document_gui(self, name):
        """Create document in GUI thread."""
        try:
            doc = FreeCAD.newDocument(name)
            doc.recompute()
            FreeCAD.Console.PrintMessage(f"Document '{name}' created via RPC.\n")
            return True
        except Exception as e:
            return str(e)

    def _create_object_gui(self, doc_name, obj: Object):
        """Create object in GUI thread."""
        doc = FreeCAD.getDocument(doc_name)
        if doc:
            try:
                if obj.type == "Fem::FemMeshGmsh" and obj.analysis:
                    from femmesh.gmshtools import GmshTools
                    res = getattr(doc, obj.analysis).addObject(ObjectsFem.makeMeshGmsh(doc, obj.name))[0]
                    if "Part" in obj.properties:
                        target_obj = doc.getObject(obj.properties["Part"])
                        if target_obj:
                            res.Part = target_obj
                        else:
                            raise ValueError(f"Referenced object '{obj.properties['Part']}' not found.")
                        del obj.properties["Part"]
                    else:
                        raise ValueError("'Part' property not found in properties.")

                    for param, value in obj.properties.items():
                        if hasattr(res, param):
                            setattr(res, param, value)
                    doc.recompute()

                    gmsh_tools = GmshTools(res)
                    gmsh_tools.create_mesh()
                    FreeCAD.Console.PrintMessage(
                        f"FEM Mesh '{res.Name}' generated successfully in '{doc_name}'.\n"
                    )
                elif obj.type.startswith("Fem::"):
                    fem_make_methods = {
                        "MaterialCommon": ObjectsFem.makeMaterialSolid,
                        "AnalysisPython": ObjectsFem.makeAnalysis,
                    }
                    obj_type_short = obj.type.split("::")[1]
                    method_name = "make" + obj_type_short
                    make_method = fem_make_methods.get(obj_type_short, getattr(ObjectsFem, method_name, None))

                    if callable(make_method):
                        res = make_method(doc, obj.name)
                        set_object_property(doc, res, obj.properties)
                        FreeCAD.Console.PrintMessage(
                            f"FEM object '{res.Name}' created with '{method_name}'.\n"
                        )
                    else:
                        raise ValueError(f"No creation method '{method_name}' found in ObjectsFem.")
                    if obj.type != "Fem::AnalysisPython" and obj.analysis:
                        getattr(doc, obj.analysis).addObject(res)
                else:
                    res = doc.addObject(obj.type, obj.name)
                    set_object_property(doc, res, obj.properties)
                    FreeCAD.Console.PrintMessage(
                        f"{res.TypeId} '{res.Name}' added to '{doc_name}' via RPC.\n"
                    )

                doc.recompute()
                return True
            except Exception as e:
                return str(e)
        else:
            FreeCAD.Console.PrintError(f"Document '{doc_name}' not found.\n")
            return f"Document '{doc_name}' not found.\n"

    def _edit_object_gui(self, doc_name: str, obj: Object):
        """Edit object in GUI thread."""
        doc = FreeCAD.getDocument(doc_name)
        if not doc:
            FreeCAD.Console.PrintError(f"Document '{doc_name}' not found.\n")
            return f"Document '{doc_name}' not found.\n"

        obj_ins = doc.getObject(obj.name)
        if not obj_ins:
            FreeCAD.Console.PrintError(f"Object '{obj.name}' not found in document '{doc_name}'.\n")
            return f"Object '{obj.name}' not found in document '{doc_name}'.\n"

        try:
            if hasattr(obj_ins, "References") and "References" in obj.properties:
                refs = []
                for ref_name, face in obj.properties["References"]:
                    ref_obj = doc.getObject(ref_name)
                    if ref_obj:
                        refs.append((ref_obj, face))
                    else:
                        raise ValueError(f"Referenced object '{ref_name}' not found.")
                obj_ins.References = refs
                FreeCAD.Console.PrintMessage(
                    f"References updated for '{obj.name}' in '{doc_name}'.\n"
                )
                del obj.properties["References"]
            set_object_property(doc, obj_ins, obj.properties)
            doc.recompute()
            FreeCAD.Console.PrintMessage(f"Object '{obj.name}' updated via RPC.\n")
            return True
        except Exception as e:
            return str(e)

    def _delete_object_gui(self, doc_name: str, obj_name: str):
        """Delete object in GUI thread."""
        doc = FreeCAD.getDocument(doc_name)
        if not doc:
            FreeCAD.Console.PrintError(f"Document '{doc_name}' not found.\n")
            return f"Document '{doc_name}' not found.\n"

        try:
            doc.removeObject(obj_name)
            doc.recompute()
            FreeCAD.Console.PrintMessage(f"Object '{obj_name}' deleted via RPC.\n")
            return True
        except Exception as e:
            return str(e)

    def _insert_part_from_library(self, relative_path):
        """Insert part from library in GUI thread."""
        try:
            insert_part_from_library(relative_path)
            return True
        except Exception as e:
            return str(e)

    def _save_active_screenshot(self, save_path: str, view_name: str = "Isometric"):
        """Save screenshot in GUI thread."""
        try:
            import time
            from pivy import coin

            view = FreeCADGui.ActiveDocument.ActiveView
            if not hasattr(view, 'saveImage'):
                return "Current view does not support screenshots"

            camera = view.getCameraNode()

            FreeCAD.Console.PrintMessage(f"[_save_active_screenshot] Requested view: {view_name}\n")

            try:
                # Use FreeCAD's built-in view methods
                if view_name == "Isometric":
                    view.viewIsometric()
                elif view_name == "Front":
                    view.viewFront()
                elif view_name == "Rear" or view_name == "Back":
                    view.viewRear()
                elif view_name == "Top":
                    view.viewTop()
                elif view_name == "Bottom":
                    view.viewBottom()
                elif view_name == "Left":
                    view.viewLeft()
                elif view_name == "Right":
                    view.viewRight()
                elif view_name in ["FrontLeft", "FrontRight", "RearLeft", "RearRight"]:
                    # Diagonal views need quaternions as FreeCAD doesn't have built-in methods
                    VIEW_QUATERNIONS = {
                        "FrontLeft": (0.17591989, 0.42470819, 0.33985114, 0.82091778),
                        "FrontRight": (0.17591989, -0.42470819, -0.33985114, 0.82091778),
                        "RearLeft": (-0.33985114, 0.82091778, 0.17591989, 0.42470819),
                        "RearRight": (-0.33985114, -0.82091778, -0.17591989, 0.42470819),
                    }
                    quat = VIEW_QUATERNIONS[view_name]
                    rot = coin.SbRotation()
                    rot.setValue(quat[0], quat[1], quat[2], quat[3])
                    camera.orientation.setValue(rot)
                else:
                    view.viewIsometric()

                # Save orientation before fitAll (fitAll can reset it)
                current_rot = camera.orientation.getValue()
                saved_quat = current_rot.getValue()
            except Exception as view_err:
                FreeCAD.Console.PrintWarning(f"Could not set view {view_name}: {view_err}\n")
                saved_quat = None

            view.fitAll()

            # Restore orientation after fitAll
            if saved_quat is not None:
                try:
                    restore_rot = coin.SbRotation()
                    restore_rot.setValue(saved_quat[0], saved_quat[1], saved_quat[2], saved_quat[3])
                    camera.orientation.setValue(restore_rot)
                except Exception as restore_err:
                    FreeCAD.Console.PrintWarning(f"Could not restore orientation: {restore_err}\n")

            # Force a repaint to ensure the view is updated
            FreeCADGui.updateGui()
            time.sleep(0.3)  # Slightly longer delay to ensure rendering completes

            # Save with explicit width and height (1920x1080)
            view.saveImage(save_path, 1920, 1080, "Current")
            return True
        except Exception as e:
            return str(e)


def start_rpc_server(host="localhost", port=9875):
    """Start the RPC server."""
    global rpc_server_thread, rpc_server_instance

    if rpc_server_instance:
        return "RPC Server already running."

    rpc_server_instance = SimpleXMLRPCServer(
        (host, port), allow_none=True, logRequests=False
    )
    rpc_server_instance.register_instance(FreeCADRPC())

    def server_loop():
        FreeCAD.Console.PrintMessage(f"CAD Repair RPC Server started at {host}:{port}\n")
        rpc_server_instance.serve_forever()

    rpc_server_thread = threading.Thread(target=server_loop, daemon=True)
    rpc_server_thread.start()

    # Start GUI task processor
    QtCore.QTimer.singleShot(500, process_gui_tasks)

    return f"RPC Server started at {host}:{port}."


def stop_rpc_server():
    """Stop the RPC server."""
    global rpc_server_instance, rpc_server_thread

    if rpc_server_instance:
        rpc_server_instance.shutdown()
        rpc_server_thread.join()
        rpc_server_instance = None
        rpc_server_thread = None
        FreeCAD.Console.PrintMessage("CAD Repair RPC Server stopped.\n")
        return "RPC Server stopped."

    return "RPC Server was not running."


class StartRPCServerCommand:
    """FreeCAD command to start the RPC server."""

    def GetResources(self):
        return {
            "MenuText": "Start RPC Server",
            "ToolTip": "Start the CAD Repair Assistant RPC Server"
        }

    def Activated(self):
        msg = start_rpc_server()
        FreeCAD.Console.PrintMessage(msg + "\n")

    def IsActive(self):
        return True


class StopRPCServerCommand:
    """FreeCAD command to stop the RPC server."""

    def GetResources(self):
        return {
            "MenuText": "Stop RPC Server",
            "ToolTip": "Stop the CAD Repair Assistant RPC Server"
        }

    def Activated(self):
        msg = stop_rpc_server()
        FreeCAD.Console.PrintMessage(msg + "\n")

    def IsActive(self):
        return True


# Register commands with FreeCAD
FreeCADGui.addCommand("Start_RPC_Server", StartRPCServerCommand())
FreeCADGui.addCommand("Stop_RPC_Server", StopRPCServerCommand())
