"""Checks the generated stand against the device envelopes and printability rules.

    python tools/check_fit.py
"""

import sys
from math import cos, radians, sin

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

    must_be_empty = {
        "Tab5 body": d.tab5(),
        "NP-F550 battery": d.battery(),
        "90° USB-C plug + cable": d.usb_plug(),
        "Stream Deck Neo (stand folded)": d.neo(),
        "Neo cable into the body": d.neo_cable(),
        "speaker grille -> channel -> side exit": d.speaker_path(),
        "nothing in front of the Tab5": d.in_front(d.tab5_outline()),
        "nothing in front of the Neo": d.in_front(g.neo_outline()),
    }
    for name, envelope in must_be_empty.items():
        clash = abs((stand ^ envelope).volume())
        report(clash < TOLERANCE_MM3, f"{name}: {clash:.2f} mm3 of overlap")

    cover = d.plug_cover()
    gap = max(0.0, cover.volume() - (stand ^ cover).volume())
    report(gap < TOLERANCE_MM3, f"USB-C plug hidden behind the face: {gap:.2f} mm3 open in front of it")
    cover = d.speaker_cover()
    gap = max(0.0, cover.volume() - (stand ^ cover).volume())
    report(gap < TOLERANCE_MM3, f"speaker channel closed at the front: {gap:.2f} mm3 open in front of it")

    # The Tab5 goes in tilted with the plug attached (and comes out the same way when the
    # stand is tipped forward). Walk that path and make sure nothing hits the stand.
    tab5_parts = d.tab5() + d.battery() + d.usb_plug_head()
    worst, where = max((abs((stand ^ d.moved(tab5_parts, m)).volume()), phase)
                       for phase, m in d.tab5_removal_path())
    report(worst < TOLERANCE_MM3, f"Tab5 + battery + plug tilt in and out of the slot: "
           f"{worst:.2f} mm3 worst overlap ({where})")

    # Downward-facing surfaces steeper than 45° from vertical, ignoring the bed.
    # Flat ones are bridges and only need a short span; sloped ones would need support.
    # The accepted exceptions are the top walls of the two slots: they have to stay square
    # to the face to keep the devices flush, which makes them 60° overhangs hidden behind
    # the devices.
    mesh = stand.to_mesh()
    verts = np.asarray(mesh.vert_properties)[:, :3]
    faces = np.asarray(mesh.tri_verts)
    tris = verts[faces]
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    area = np.linalg.norm(n, axis=1) / 2
    nz = n[:, 2] / (2 * area + 1e-12)
    on_bed = tris[:, :, 2].max(axis=1) < 0.01
    bad = (nz < -cos(radians(45)) - 1e-6) & ~on_bed
    u, v, w = ((tris.mean(axis=1) - g.FACE[:, 3]) @ g.FACE[:, :3]).T
    steep_ok = -nz < sin(radians(60.5))
    slot_tops = {
        "Neo": (v > g.NEO_H / 2) & (v < g.NEO_TOP + 0.3) & (w > -g.NEO_T - 0.1)
        & (np.abs(u) < g.NEO_W / 2 + g.CLEAR + 0.1),
        "Tab5": (v > g.V_TAB + g.TAB5_H / 2) & (v < g.V_TOP + g.CLEAR + 0.3)
        & (w > -g.TAB5_T - 0.1) & (np.abs(u) < g.TAB5_W / 2 + g.CLEAR + 0.1),
    }
    known = np.zeros_like(bad)
    for name, region in slot_tops.items():
        hit = bad & region & steep_ok
        known |= hit
        report(hit.any(), f"{name} slot top wall: {area[hit].sum():.0f} mm2 at up to "
               f"{np.degrees(np.arcsin(-nz[hit].min())):.0f}° (accepted, hidden behind it)")
    for idx in surface_patches(faces, np.flatnonzero(bad & ~known)):
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
