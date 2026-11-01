"""Checks the generated stand against the device envelopes and printability rules.

    python tools/check_fit.py
"""

import re
import sys
import zipfile
from math import cos, radians, sin

import numpy as np
from manifold3d import JoinType

import devices as d
from devices import g

TOLERANCE_MM3 = 0.5
# Narrowest livery stroke or gap. Printed upright, each layer cuts the 0.6 mm inlay into
# thin strips, so across the slope (u) a feature has to span a few extrusion widths;
# up the slope (v) it only needs a few layers.
MIN_FEATURE_U, MIN_FEATURE_V = 1.4, 0.7


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


def topology(manifold):
    """(coincident vertices, zero-area triangles) once the mesh is reduced to positions."""
    tris = d.manifold_triangles(manifold)
    corners = np.unique(tris.reshape(-1, 3).round(5), axis=0)
    tiny = np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1) < 1e-8
    return len(manifold.to_mesh().vert_properties) - len(corners), int(tiny.sum())


def read_3mf(path):
    """{part name: (vertices, triangles)} for every mesh object in a 3MF file."""
    model = zipfile.ZipFile(path).read("3D/3dmodel.model").decode()
    parts = {}
    for name, body in re.findall(r'<object id="\d+" name="([^"]*)" type="model"><mesh>(.*?)</mesh>', model):
        verts = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"/>', body), float)
        tris = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"/>', body), int)
        parts[name] = verts, tris
    return parts


def closed_volume(verts, tris):
    """Volume of a mesh, or None unless every edge is used once in each direction."""
    edges = np.vstack([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    forward = {tuple(e) for e in edges}
    if len(forward) != len(edges) or any((b, a) not in forward for a, b in forward):
        return None
    a, b, c = (verts[tris[:, i]] for i in range(3))
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6)


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
    merged, tiny = topology(stand)
    report(not merged and not tiny,
           f"clean STL topology ({merged} coincident vertices, {tiny} zero-area triangles)")

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

    # Two-filament version: the livery inlay and the stand it is recessed into.
    body, inlay = g.build_parts(stand)
    for name, part in (("stand with recess", body), ("ornament inlay", inlay)):
        merged, tiny = topology(part)
        report(part.status().name == "NoError" and not part.is_empty() and not merged and not tiny,
               f"{name}: valid manifold, clean topology ({merged} coincident vertices, "
               f"{tiny} zero-area triangles)")
    overlap = (body ^ inlay).volume()
    missing = abs(body.volume() + inlay.volume() - stand.volume())
    report(overlap < TOLERANCE_MM3 and missing < TOLERANCE_MM3,
           f"stand + ornament = one-colour stand ({overlap:.2f} mm3 overlap, {missing:.2f} mm3 apart)")
    # Full depth everywhere: the livery stays on the flat face, clear of the rounded edges
    # and the slots, so no part of the inlay thins out to a sliver.
    livery = g.ornament()
    thin = livery.area() * g.ORNAMENT_DEPTH - inlay.volume()
    report(abs(thin) < TOLERANCE_MM3,
           f"ornament inlaid {g.ORNAMENT_DEPTH} mm deep everywhere: {thin:.2f} mm3 short")
    scaled = livery.scale((1, MIN_FEATURE_U / MIN_FEATURE_V))
    r = MIN_FEATURE_U / 2
    opened = scaled.offset(-r, JoinType.Miter, 10).offset(r, JoinType.Miter, 10)
    closed = scaled.offset(r, JoinType.Miter, 10).offset(-r, JoinType.Miter, 10)
    lost, filled = (scaled - opened).area(), (closed - scaled).area()
    report(lost < 0.5 and filled < 0.5,
           f"ornament strokes and gaps at least {MIN_FEATURE_U} mm across the slope and "
           f"{MIN_FEATURE_V} mm up it ({lost:.2f} mm2 thinner, {filled:.2f} mm2 narrower)")
    print(f"       ornament: {inlay.volume():.0f} mm3, in {g.colour_layers(inlay)} of the 0.2 mm layers")

    # The written 3MF: one closed mesh per part, matching the model.
    parts = read_3mf(g.OUT_3MF)
    volumes = {name: closed_volume(*mesh) for name, mesh in parts.items()}
    expected = {"stand": body.volume(), "ornament": inlay.volume()}
    report(volumes.keys() == expected.keys()
           and all(volumes[k] is not None and abs(volumes[k] - expected[k]) < TOLERANCE_MM3
                   for k in expected),
           f"{g.OUT_3MF.name}: closed meshes " + ", ".join(
               f"{k} {v / 1000:.3f} cm3" if v is not None else f"{k} open" for k, v in volumes.items()))

    lo, hi = np.array(stand.bounding_box()).reshape(2, 3)
    print(f"       size {hi[0] - lo[0]:.1f} x {hi[1] - lo[1]:.1f} x {hi[2] - lo[2]:.1f} mm")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
