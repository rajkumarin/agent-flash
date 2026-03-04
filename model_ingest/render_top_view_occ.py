"""Render top-view PNG from a STEP model using OpenCascade (OCP bindings)."""

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
from OCP.Poly import Poly_Triangulation
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.TopLoc import TopLoc_Location


def load_step_shape(step_path: Path):
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(step_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to read STEP file: {step_path}")

    nb_roots = reader.NbRootsForTransfer()
    if nb_roots < 1:
        raise RuntimeError("No roots available for transfer in STEP file")

    transferred = 0
    for idx in range(1, nb_roots + 1):
        if reader.TransferRoot(idx):
            transferred += 1

    if transferred == 0:
        raise RuntimeError("No transferable roots found in STEP file")

    shape = reader.OneShape()
    if shape.IsNull():
        raise RuntimeError("Transferred shape is null")
    return shape


def mesh_shape(shape, linear_deflection: float = 0.4, angular_deflection: float = 0.5):
    mesher = BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection, True)
    mesher.Perform()


def extract_top_view_triangles(shape):
    triangles_xy = []
    triangle_z = []

    exp = TopExp_Explorer(shape, TopAbs_FACE)

    while exp.More():
        face = TopoDS.Face_s(exp.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)

        if tri is not None and isinstance(tri, Poly_Triangulation):
            trsf = loc.Transformation()
            nodes = tri.Nodes()
            tris = tri.Triangles()

            for i in range(1, tri.NbTriangles() + 1):
                t = tris.Value(i)
                i1, i2, i3 = t.Value(1), t.Value(2), t.Value(3)

                p1 = nodes.Value(i1).Transformed(trsf)
                p2 = nodes.Value(i2).Transformed(trsf)
                p3 = nodes.Value(i3).Transformed(trsf)

                poly = [(p1.X(), p1.Y()), (p2.X(), p2.Y()), (p3.X(), p3.Y())]
                zavg = (p1.Z() + p2.Z() + p3.Z()) / 3.0

                triangles_xy.append(poly)
                triangle_z.append(zavg)

        exp.Next()

    if not triangles_xy:
        raise RuntimeError("No triangulated faces found in STEP shape")

    return triangles_xy, np.array(triangle_z)


def render_top_view(step_path: Path, output_png: Path):
    shape = load_step_shape(step_path)
    mesh_shape(shape)
    polys, zvals = extract_top_view_triangles(shape)

    order = np.argsort(zvals)
    sorted_polys = [polys[i] for i in order]

    fig = plt.figure(figsize=(10, 10), dpi=220)
    ax = fig.add_subplot(111)

    coll = PolyCollection(
        sorted_polys,
        facecolors="#f2f2f2",
        edgecolors="#202020",
        linewidths=0.12,
    )
    ax.add_collection(coll)

    all_xy = np.array([pt for poly in sorted_polys for pt in poly])
    min_xy = all_xy.min(axis=0)
    max_xy = all_xy.max(axis=0)
    span = np.maximum(max_xy - min_xy, 1e-6)
    pad = 0.06 * span

    ax.set_xlim(min_xy[0] - pad[0], max_xy[0] + pad[0])
    ax.set_ylim(min_xy[1] - pad[1], max_xy[1] + pad[1])
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title("Top View (OpenCascade)", fontsize=12)

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--step", required=True, help="Path to STEP file")
    p.add_argument("--out", required=True, help="Output PNG path")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    step = Path(args.step)
    out = Path(args.out)
    render_top_view(step, out)
    print(f"Rendered: {out}")
