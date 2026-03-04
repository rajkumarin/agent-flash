"""Render assembled top-view PNG from external-reference STEP assembly using OCC (OCP)."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.STEPControl import STEPControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label, TDF_LabelSequence
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_DocumentTool


def load_part_shape(step_path: Path):
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(step_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to read part STEP: {step_path}")
    nroots = reader.NbRootsForTransfer()
    for i in range(1, nroots + 1):
        reader.TransferRoot(i)
    shape = reader.OneShape()
    if shape.IsNull():
        raise RuntimeError(f"Null part shape: {step_path}")
    return shape


def mesh_shape(shape, linear_deflection: float = 0.25, angular_deflection: float = 0.5):
    BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection, True).Perform()


def extract_triangles_local(shape):
    polys = []
    zvals = []

    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = TopoDS.Face_s(exp.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri is None:
            exp.Next()
            continue

        trsf = loc.Transformation()
        for i in range(1, tri.NbTriangles() + 1):
            t = tri.Triangle(i)
            i1, i2, i3 = t.Value(1), t.Value(2), t.Value(3)
            p1 = tri.Node(i1).Transformed(trsf)
            p2 = tri.Node(i2).Transformed(trsf)
            p3 = tri.Node(i3).Transformed(trsf)

            poly = [(p1.X(), p1.Y(), p1.Z()), (p2.X(), p2.Y(), p2.Z()), (p3.X(), p3.Y(), p3.Z())]
            polys.append(poly)
            zvals.append((p1.Z() + p2.Z() + p3.Z()) / 3.0)

        exp.Next()

    return polys, zvals


def load_assembly_instances(assembly_step: Path):
    doc = TDocStd_Document(TCollection_ExtendedString("ocaf"))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)

    status = reader.ReadFile(str(assembly_step))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to read assembly STEP: {assembly_step}")
    if not reader.Transfer(doc):
        raise RuntimeError("Failed to transfer assembly STEP into OCAF document")

    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    roots = TDF_LabelSequence()
    shape_tool.GetFreeShapes(roots)
    if roots.Length() < 1:
        raise RuntimeError("Assembly has no free root shapes")

    root = roots.Value(1)
    comps = TDF_LabelSequence()
    shape_tool.GetComponents_s(root, comps)

    name_guid = TDataStd_Name.GetID_s()
    instances: list[tuple[str, object]] = []

    for i in range(1, comps.Length() + 1):
        comp_lbl = comps.Value(i)
        ref_lbl = TDF_Label()
        if not shape_tool.GetReferredShape_s(comp_lbl, ref_lbl):
            continue

        name_attr = TDataStd_Name()
        if not ref_lbl.FindAttribute(name_guid, name_attr):
            continue

        ref_name = name_attr.Get().ToExtString().strip()
        if not ref_name:
            continue

        loc = shape_tool.GetLocation_s(comp_lbl)
        instances.append((ref_name, loc.Transformation()))

    if not instances:
        raise RuntimeError("No assembly component instances found")

    return instances


def render_top_view(assembly_step: Path, parts_dir: Path, output_png: Path):
    instances = load_assembly_instances(assembly_step)

    part_file_map = {p.stem: p for p in parts_dir.glob("*.STEP")}

    tri_cache: dict[str, tuple[list[list[tuple[float, float, float]]], list[float]]] = {}
    polys_2d = []
    zvals = []
    misses = []

    for ref_name, comp_trsf in instances:
        part_path = part_file_map.get(ref_name)
        if part_path is None:
            misses.append(ref_name)
            continue

        if ref_name not in tri_cache:
            shape = load_part_shape(part_path)
            mesh_shape(shape)
            tri_cache[ref_name] = extract_triangles_local(shape)

        local_polys, _ = tri_cache[ref_name]
        for tri in local_polys:
            gp = []
            for x, y, z in tri:
                # apply component placement transform
                from OCP.gp import gp_Pnt

                p = gp_Pnt(x, y, z).Transformed(comp_trsf)
                gp.append((p.X(), p.Y(), p.Z()))

            polys_2d.append([(gp[0][0], gp[0][1]), (gp[1][0], gp[1][1]), (gp[2][0], gp[2][1])])
            zvals.append((gp[0][2] + gp[1][2] + gp[2][2]) / 3.0)

    if not polys_2d:
        raise RuntimeError("No assembled triangles produced")

    order = np.argsort(np.array(zvals))
    sorted_polys = [polys_2d[i] for i in order]

    fig = plt.figure(figsize=(10, 10), dpi=220)
    ax = fig.add_subplot(111)

    coll = PolyCollection(sorted_polys, facecolors="#efefef", edgecolors="#202020", linewidths=0.12)
    ax.add_collection(coll)

    all_xy = np.array([pt for poly in sorted_polys for pt in poly])
    mn = all_xy.min(axis=0)
    mx = all_xy.max(axis=0)
    pad = 0.06 * np.maximum(mx - mn, 1e-6)

    ax.set_xlim(mn[0] - pad[0], mx[0] + pad[0])
    ax.set_ylim(mn[1] - pad[1], mx[1] + pad[1])
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title("Top View (OCC Assembled)", fontsize=12)

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)

    if misses:
        print(f"Missing part files ({len(set(misses))} unique):")
        for m in sorted(set(misses)):
            print(f"  - {m}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--assembly", required=True)
    ap.add_argument("--parts-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    render_top_view(Path(args.assembly), Path(args.parts_dir), Path(args.out))
    print(f"Rendered: {args.out}")
