"""
Serialization utilities for FreeCAD objects.

This module converts FreeCAD objects to dictionaries that can be
transmitted over XML-RPC.
"""

import FreeCAD


def serialize_placement(placement):
    """Serialize a FreeCAD Placement object."""
    if placement is None:
        return None

    base = placement.Base
    rotation = placement.Rotation

    return {
        "Base": {
            "x": base.x,
            "y": base.y,
            "z": base.z
        },
        "Rotation": {
            "Axis": {
                "x": rotation.Axis.x,
                "y": rotation.Axis.y,
                "z": rotation.Axis.z
            },
            "Angle": rotation.Angle
        }
    }


def serialize_vector(vector):
    """Serialize a FreeCAD Vector object."""
    if vector is None:
        return None

    return {
        "x": vector.x,
        "y": vector.y,
        "z": vector.z
    }


def serialize_bounding_box(bbox):
    """Serialize a FreeCAD BoundBox object."""
    if bbox is None:
        return None

    return {
        "XMin": bbox.XMin,
        "XMax": bbox.XMax,
        "YMin": bbox.YMin,
        "YMax": bbox.YMax,
        "ZMin": bbox.ZMin,
        "ZMax": bbox.ZMax,
        "XLength": bbox.XLength,
        "YLength": bbox.YLength,
        "ZLength": bbox.ZLength
    }


def serialize_property(obj, prop_name):
    """Serialize a single property value."""
    try:
        value = getattr(obj, prop_name)

        # Handle special types
        if isinstance(value, FreeCAD.Placement):
            return serialize_placement(value)
        elif isinstance(value, FreeCAD.Vector):
            return serialize_vector(value)
        elif isinstance(value, FreeCAD.BoundBox):
            return serialize_bounding_box(value)
        elif isinstance(value, (int, float, str, bool, type(None))):
            return value
        elif isinstance(value, (list, tuple)):
            # Try to serialize list items
            serialized = []
            for item in value:
                if isinstance(item, (int, float, str, bool, type(None))):
                    serialized.append(item)
                elif isinstance(item, FreeCAD.Vector):
                    serialized.append(serialize_vector(item))
                else:
                    serialized.append(str(item))
            return serialized
        else:
            # Return string representation for complex types
            return str(value)
    except Exception as e:
        return f"<Error reading property: {e}>"


def serialize_object(obj):
    """
    Serialize a FreeCAD DocumentObject to a dictionary.

    Args:
        obj: FreeCAD DocumentObject

    Returns:
        Dictionary with object properties
    """
    if obj is None:
        return None

    # Basic object info
    data = {
        "Name": obj.Name,
        "Label": obj.Label,
        "TypeId": obj.TypeId,
    }

    # Get placement if available
    if hasattr(obj, "Placement"):
        data["Placement"] = serialize_placement(obj.Placement)

    # Get shape bounding box if available
    if hasattr(obj, "Shape") and obj.Shape:
        try:
            data["BoundingBox"] = serialize_bounding_box(obj.Shape.BoundBox)
        except Exception:
            pass

    # Get common properties
    common_props = [
        "Length", "Width", "Height", "Radius", "Radius1", "Radius2",
        "Angle", "Angle1", "Angle2", "Axis", "Base", "Tool",
        "Visibility", "ViewObject"
    ]

    properties = {}
    for prop in common_props:
        if prop in obj.PropertiesList:
            properties[prop] = serialize_property(obj, prop)

    # Get dimensions for specific types
    if obj.TypeId == "Part::Box":
        for prop in ["Length", "Width", "Height"]:
            if prop in obj.PropertiesList:
                properties[prop] = serialize_property(obj, prop)
    elif obj.TypeId == "Part::Cylinder":
        for prop in ["Radius", "Height", "Angle"]:
            if prop in obj.PropertiesList:
                properties[prop] = serialize_property(obj, prop)
    elif obj.TypeId == "Part::Sphere":
        for prop in ["Radius", "Angle1", "Angle2", "Angle3"]:
            if prop in obj.PropertiesList:
                properties[prop] = serialize_property(obj, prop)
    elif obj.TypeId == "Part::Cone":
        for prop in ["Radius1", "Radius2", "Height", "Angle"]:
            if prop in obj.PropertiesList:
                properties[prop] = serialize_property(obj, prop)
    elif obj.TypeId == "Part::Torus":
        for prop in ["Radius1", "Radius2", "Angle1", "Angle2", "Angle3"]:
            if prop in obj.PropertiesList:
                properties[prop] = serialize_property(obj, prop)

    if properties:
        data["Properties"] = properties

    # Get view properties if available
    if hasattr(obj, "ViewObject") and obj.ViewObject:
        view_props = {}
        vo = obj.ViewObject

        if hasattr(vo, "ShapeColor"):
            try:
                color = vo.ShapeColor
                view_props["ShapeColor"] = [color[0], color[1], color[2], color[3] if len(color) > 3 else 1.0]
            except Exception:
                pass

        if hasattr(vo, "Transparency"):
            try:
                view_props["Transparency"] = vo.Transparency
            except Exception:
                pass

        if hasattr(vo, "Visibility"):
            try:
                view_props["Visibility"] = vo.Visibility
            except Exception:
                pass

        if view_props:
            data["ViewObject"] = view_props

    return data


def serialize_document(doc):
    """
    Serialize a FreeCAD Document to a dictionary.

    Args:
        doc: FreeCAD Document

    Returns:
        Dictionary with document info and objects
    """
    if doc is None:
        return None

    return {
        "Name": doc.Name,
        "Label": doc.Label,
        "ObjectCount": len(doc.Objects),
        "Objects": [serialize_object(obj) for obj in doc.Objects]
    }
