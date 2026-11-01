"""Checks the generated stand against the device envelopes and printability rules.

    python tools/check_fit.py
"""

import sys
from math import cos, radians

import numpy as np

import devices as d
from devices import g

TOLERANCE_MM3 = 0.5


def surface_patches(faces, selected):
    """Group selected triangles into patches that share vertices."""
    parent = {int(i): int(i) for i in selected}

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    by_vertex = {}
    for i in selected:
        for v in faces[i]:
            j = by_vertex.setdefault(int(v), int(i))
            parent[root(int(i))] = root(j)
    groups = {}
    for i in selected:
        groups.setdefault(root(int(i)), []).append(int(i))
    return sorted(groups.values(), key=lambda idx: faces[idx].min())


def main():
    stand = g.build()
    failures = 0

    def report(ok, text):
        nonlocal failures
        failures += not ok
        print(f"[{'ok' if ok else 'FAIL'}] {text}")

    report(stand.status().name == "NoError" and not stand.is_empty(),
           f"solid is a valid manifold (genus {stand.genus()}, {stand.volume() / 1000:.0f} cm3)")

    # Slicers merge STL vertices by position, so touching geometry must not leave
    # coincident vertices or zero-area triangles behind.
    tris = d.manifold_triangles(stand)
    corners = np.unique(tris.reshape(-1, 3).round(5), axis=0)
    mesh = stand.to_mesh()
    tiny = np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1) < 1e-8
    report(len(corners) == len(mesh.vert_properties) and not tiny.any(),
           f"clean STL topology ({len(mesh.vert_properties) - len(corners)} coincident vertices, "
           f"{tiny.sum()} zero-area triangles)")

    tab5_u0, tab5_u1 = d.tab5_x_range(0, g.TAB5_W)
    must_be_empty = {
        "Tab5 body": d.tab5(),
        "NP-F550 battery": d.battery(),
        "90° USB-C plug + cable": d.usb_plug(),
        "Stream Deck Neo (stand folded)": d.neo(),
        "Neo cable into the body": d.neo_cable(),
        "speaker grille -> sound gap": d.speaker_path(),
        "nothing in front of the Tab5": d.front_projection(tab5_u0, tab5_u1, g.V_TAB, g.V_TOP, g.STEP),
        "nothing in front of the Neo": d.front_projection(-g.NEO_W / 2, g.NEO_W / 2, 0, g.NEO_H, 0),
    }
    for name, envelope in must_be_empty.items():
        clash = abs((stand ^ envelope).volume())
        report(clash < TOLERANCE_MM3, f"{name}: {clash:.2f} mm3 of overlap")

    # Downward-facing surfaces steeper than 45° from vertical, ignoring the bed.
    # Flat ones are bridges and only need a short span; sloped ones would need support.
    mesh = stand.to_mesh()
    verts = np.asarray(mesh.vert_properties)[:, :3]
    faces = np.asarray(mesh.tri_verts)
    tris = verts[faces]
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    area = np.linalg.norm(n, axis=1) / 2
    nz = n[:, 2] / (2 * area + 1e-12)
    on_bed = tris[:, :, 2].max(axis=1) < 0.01
    bad = (nz < -cos(radians(45)) - 1e-6) & ~on_bed
    for idx in surface_patches(faces, np.flatnonzero(bad)):
        pts = tris[idx].reshape(-1, 3)
        z = pts[:, 2].mean()
        if (nz[idx] < -0.999).all():
            span = (pts[:, :2].max(0) - pts[:, :2].min(0)).min()
            report(span < 25, f"bridge at Z={z:.1f}: {span:.1f} mm span")
        else:
            report(area[idx].sum() < 1.0, f"sloped overhang at Z={z:.1f}: {area[idx].sum():.1f} mm2")

    lo, hi = np.array(stand.bounding_box()).reshape(2, 3)
    print(f"       size {hi[0] - lo[0]:.1f} x {hi[1] - lo[1]:.1f} x {hi[2] - lo[2]:.1f} mm")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
