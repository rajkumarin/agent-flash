"""
Parts Library utilities for CAD Repair MCP.

This module provides access to FreeCAD's parts library for
inserting pre-made components.
"""

import os
import FreeCAD
import FreeCADGui

# Default parts library paths
PARTS_LIBRARY_PATHS = [
    # FreeCAD's default parts library location
    os.path.join(FreeCAD.getResourceDir(), "Mod", "Parts"),
    # User's parts library
    os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "parts_library"),
    # Additional common locations
    os.path.expanduser("~/FreeCAD/Parts"),
]


def get_parts_library_path():
    """Get the first available parts library path."""
    for path in PARTS_LIBRARY_PATHS:
        if os.path.isdir(path):
            return path

    # Create user parts directory if none exists
    user_parts = os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "parts_library")
    os.makedirs(user_parts, exist_ok=True)
    return user_parts


def get_parts_list(base_path=None):
    """
    Get a list of all available parts in the library.

    Args:
        base_path: Optional base path to search. If None, uses default.

    Returns:
        List of relative paths to part files (.FCStd, .step, .stp, .iges, .igs)
    """
    if base_path is None:
        base_path = get_parts_library_path()

    if not os.path.isdir(base_path):
        return []

    parts = []
    valid_extensions = {'.fcstd', '.step', '.stp', '.iges', '.igs', '.brep', '.brp'}

    for root, dirs, files in os.walk(base_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_extensions:
                # Get relative path
                rel_path = os.path.relpath(os.path.join(root, file), base_path)
                parts.append(rel_path.replace('\\', '/'))

    return sorted(parts)


def insert_part_from_library(relative_path, base_path=None):
    """
    Insert a part from the library into the active document.

    Args:
        relative_path: Relative path to the part file
        base_path: Optional base path. If None, uses default.

    Returns:
        The inserted object or raises an exception
    """
    if base_path is None:
        base_path = get_parts_library_path()

    full_path = os.path.join(base_path, relative_path)

    if not os.path.isfile(full_path):
        raise FileNotFoundError(f"Part file not found: {full_path}")

    # Get or create active document
    doc = FreeCAD.ActiveDocument
    if doc is None:
        doc = FreeCAD.newDocument("Imported")

    ext = os.path.splitext(full_path)[1].lower()

    if ext == '.fcstd':
        # For FreeCAD files, merge the document
        import_doc = FreeCAD.openDocument(full_path)
        for obj in import_doc.Objects:
            # Copy object to active document
            doc.copyObject(obj, True)
        FreeCAD.closeDocument(import_doc.Name)
    else:
        # For STEP, IGES, BREP files, use import
        import Part
        shape = Part.read(full_path)

        # Create a Part::Feature to hold the shape
        part_name = os.path.splitext(os.path.basename(relative_path))[0]
        part_obj = doc.addObject("Part::Feature", part_name)
        part_obj.Shape = shape

    doc.recompute()
    FreeCAD.Console.PrintMessage(f"Inserted part from library: {relative_path}\n")

    return True


def create_sample_car_parts():
    """
    Create a set of sample car parts in the parts library.

    This is useful for testing and demonstration purposes.
    """
    library_path = get_parts_library_path()
    car_parts_path = os.path.join(library_path, "CarParts")
    os.makedirs(car_parts_path, exist_ok=True)

    # List of sample parts to create
    sample_parts = [
        ("Wheel", create_wheel_part),
        ("Headlight", create_headlight_part),
        ("Mirror", create_mirror_part),
    ]

    created = []
    for name, creator in sample_parts:
        try:
            part_path = os.path.join(car_parts_path, f"{name}.FCStd")
            if not os.path.exists(part_path):
                creator(part_path)
                created.append(name)
        except Exception as e:
            FreeCAD.Console.PrintError(f"Failed to create {name}: {e}\n")

    return created


def create_wheel_part(save_path):
    """Create a simple wheel part."""
    doc = FreeCAD.newDocument("Wheel")

    # Create tire (torus)
    tire = doc.addObject("Part::Torus", "Tire")
    tire.Radius1 = 30  # Major radius
    tire.Radius2 = 10  # Minor radius

    # Create rim (cylinder)
    rim = doc.addObject("Part::Cylinder", "Rim")
    rim.Radius = 20
    rim.Height = 15

    # Create hub (cylinder)
    hub = doc.addObject("Part::Cylinder", "Hub")
    hub.Radius = 5
    hub.Height = 20

    doc.recompute()
    doc.saveAs(save_path)
    FreeCAD.closeDocument(doc.Name)


def create_headlight_part(save_path):
    """Create a simple headlight part."""
    doc = FreeCAD.newDocument("Headlight")

    # Create lens (sphere)
    lens = doc.addObject("Part::Sphere", "Lens")
    lens.Radius = 15

    # Create housing (cylinder)
    housing = doc.addObject("Part::Cylinder", "Housing")
    housing.Radius = 18
    housing.Height = 10
    housing.Placement.Base.y = -10

    doc.recompute()
    doc.saveAs(save_path)
    FreeCAD.closeDocument(doc.Name)


def create_mirror_part(save_path):
    """Create a simple side mirror part."""
    doc = FreeCAD.newDocument("Mirror")

    # Create mirror housing (box)
    housing = doc.addObject("Part::Box", "Housing")
    housing.Length = 15
    housing.Width = 10
    housing.Height = 5

    # Create arm (cylinder)
    arm = doc.addObject("Part::Cylinder", "Arm")
    arm.Radius = 2
    arm.Height = 10
    arm.Placement.Base.x = 7.5
    arm.Placement.Base.y = 5

    doc.recompute()
    doc.saveAs(save_path)
    FreeCAD.closeDocument(doc.Name)
