"""Parametric desk stand for an M5Stack Tab5 (landscape) and an Elgato Stream Deck Neo.

    python generate_stand.py            -> writes stl/tab5_neo_stand.stl

Both devices sit in slots, flush with the front face of the stand. The Tab5 slides in
from the top, and its 90° USB-C plug rides down a channel hidden under the face. The
Neo drops into a slot cut to its real outline. Both cables run through the hollow body
to a rear exit. All dimensions are in millimetres.

Output coordinates: X = width (left to right, seen from the front), Y = depth
(front to back), Z = up. The stand prints upright, exactly as it sits on the desk.

Features are placed in the frame of the inclined face:
    u  along X (0 = centre of the stand)
    v  up the slope (0 = bottom edge of the Neo)
    w  out of the face, towards the user (0 = front face; slots go into negative w)
"""

from math import cos, radians, sin, tan
from pathlib import Path

import numpy as np
from manifold3d import CrossSection, JoinType, Manifold, OpType, set_circular_segments

# --------------------------------------------------------------------------
# Devices
# --------------------------------------------------------------------------
# M5Stack Tab5, landscape, seen from the front, origin at the bottom-left corner.
# Official drawing / STL: https://github.com/m5stack/M5_Hardware (C145_Tab5)
TAB5_W, TAB5_H, TAB5_T, TAB5_R = 128.0, 80.0, 12.0, 4.0
TAB5_BATTERY = (81.2, 9.5, 119.4, 79.9)  # NP-F550 footprint on the back: x0, y0, x1, y1
TAB5_BATTERY_PROTRUSION = 14.7           # Tab5 Kit 26.7 mm - bare Tab5 12.0 mm
TAB5_SPEAKER_X = (91.5, 110.5)           # speaker grille on the bottom edge
TAB5_SPEAKER_DEPTH = (2.0, 6.0)          # grille band, measured from the back face
TAB5_USBC_Y = 40.0                       # USB-C centre on the left edge
TAB5_USBC_DEPTH = 2.5                    # USB-C centre measured from the back face
TAB5_MIRROR = False                      # True if your USB-C ends up on the right side

# Elgato Stream Deck Neo. Right half of the front outline (u, v), bottom centre to top
# centre, traced from Elgato's official device model render (107 x 78 mm).
NEO_OUTLINE_RIGHT = [
    (0.00, 0.00), (1.36, 0.00), (2.73, 0.00), (4.10, 0.01), (5.48, 0.06), (6.86, 0.11),
    (8.27, 0.11), (9.70, 0.12), (11.16, 0.11), (12.64, 0.12), (14.16, 0.12), (15.69, 0.18),
    (17.27, 0.23), (18.90, 0.26), (20.57, 0.33), (22.33, 0.35), (24.12, 0.41), (26.00, 0.48),
    (27.95, 0.54), (30.01, 0.61), (32.17, 0.68), (34.43, 0.78), (36.78, 0.93), (39.12, 1.24),
    (41.41, 1.73), (43.61, 2.42), (45.62, 3.37), (47.39, 4.58), (48.89, 6.04), (50.13, 7.69),
    (51.09, 9.52), (51.80, 11.47), (52.31, 13.50), (52.66, 15.57), (52.87, 17.66),
    (53.01, 19.72), (53.11, 21.76), (53.17, 23.77), (53.24, 25.74), (53.29, 27.69),
    (53.35, 29.61), (53.40, 31.51), (53.46, 33.40), (53.49, 35.28), (53.50, 37.15),
    (53.50, 39.02), (53.50, 40.89), (53.49, 42.76), (53.49, 44.64), (53.49, 46.53),
    (53.46, 48.44), (53.44, 50.38), (53.40, 52.33), (53.34, 54.31), (53.30, 56.34),
    (53.22, 58.39), (53.11, 60.47), (52.89, 62.57), (52.52, 64.63), (51.96, 66.65),
    (51.17, 68.56), (50.15, 70.36), (48.87, 71.98), (47.28, 73.37), (45.46, 74.54),
    (43.52, 75.53), (41.40, 76.29), (39.09, 76.77), (36.74, 77.06), (34.42, 77.24),
    (32.17, 77.35), (30.01, 77.43), (27.97, 77.52), (26.01, 77.58), (24.14, 77.65),
    (22.34, 77.70), (20.59, 77.74), (18.92, 77.81), (17.27, 77.81), (15.69, 77.85),
    (14.16, 77.92), (12.64, 77.92), (11.16, 77.92), (9.70, 77.92), (8.27, 77.94),
    (6.88, 78.01), (5.48, 78.03), (4.10, 78.03), (2.73, 78.03), (1.36, 78.03), (0.00, 78.04),
]
NEO_T = 26.0        # body ~20 mm plus its integrated stand folded flat (official spec)
NEO_CABLE_V = 40.0  # the captive cable leaves the middle of the back

# --------------------------------------------------------------------------
# Stand
# --------------------------------------------------------------------------
TILT = 60.0           # face angle from the desk
WALL = 2.4            # shell wall
FLOOR = 3.0           # bottom plate
EDGE_R = 1.6          # rounding of the outer edges
CLEAR = 0.5           # gap around each device in its slot
SIDE = 20.0           # frame each side of the Tab5; the left one hides the USB-C plug
BOTTOM = 6.5          # frame below the Neo
NEO_Z = 18.0          # height of the Neo's bottom front edge above the desk
STRIP = 3.0           # frame between the Neo slot and the speaker port
SPEAKER_PORT = 7.0    # speaker port height below the Tab5 (it opens to the front)
REAR_LEAN = 8.0       # rear foot sticks out this much further back than the top
MAX_OVERHANG = 40.0   # steepest printed overhang, degrees from vertical

PLUG = (13.0, 13.0, 7.0)  # 90° USB-C plug: length out of the port, width, thickness
PLUG_CLEAR = 0.8
CABLE_SLOT = 6.5          # slot the plug's cable slides down
BATTERY_CLEAR = 1.0       # each side of the battery notch
NEO_HOLE = (40.0, 44.0)   # cable hole in the Neo slot floor: width, height
NEO_GRIP = (13.0, 12.0)   # finger scoops beside the Neo: half length, depth at the slot
REAR_EXIT = (56.0, 30.0)  # cable exit in the back wall: width, height
FOOT_D, FOOT_DEPTH, FOOT_INSET = 10.5, 1.0, 12.0  # recesses for stick-on rubber feet

OUT = Path(__file__).parent / "stl" / "tab5_neo_stand.stl"

# --------------------------------------------------------------------------
# Derived geometry
# --------------------------------------------------------------------------
WIDTH = TAB5_W + 2 * SIDE
C, S = cos(radians(TILT)), sin(radians(TILT))
# A surface that rises "h" off the slope over a run "d" up the slope leans forward by
# atan(h/d) - (90° - TILT) from vertical, so it stays printable when d/h >= this:
RUN_PER_RISE = tan(radians(TILT - MAX_OVERHANG))
A = (0.0, NEO_Z)                         # (Y, Z) of the Neo's bottom front edge
NEO_W = 2 * max(u for u, _ in NEO_OUTLINE_RIGHT)
NEO_H = max(v for _, v in NEO_OUTLINE_RIGHT)
NEO_TOP = NEO_H + CLEAR                  # top edge of the Neo slot
V_TAB = NEO_TOP + STRIP + SPEAKER_PORT   # bottom edge of the Tab5
V_TOP = V_TAB + TAB5_H                   # top edge of the Tab5 = top of the face
PLUG_W = -TAB5_T + TAB5_USBC_DEPTH       # w of the USB-C centre line
CHANNEL = (PLUG_W - PLUG[2] / 2 - PLUG_CLEAR, PLUG_W + PLUG[2] / 2 + PLUG_CLEAR)
UPPER_DEPTH = -CHANNEL[0] + WALL         # solid frame around the Tab5 slot and channel
BATTERY_W = -TAB5_T - TAB5_BATTERY_PROTRUSION - 1.5
LOWER_DEPTH = max(NEO_T, -BATTERY_W) + WALL  # solid frame around the Neo slot
LOWER_TOP = V_TAB + TAB5_BATTERY[1]      # solid frame ends where the battery notch starts
TOP_DEPTH = (LOWER_DEPTH + WALL + 1.0) / S

set_circular_segments(64)


def vw(v, w):
    """(v, w) on the slope -> (Y, Z) in the side profile."""
    return (A[0] + v * C - w * S, A[1] + v * S + w * C)


def tab5_u(x):
    """Tab5 x (from its left edge) -> u on the stand."""
    return (TAB5_W / 2 - x) if TAB5_MIRROR else (x - TAB5_W / 2)


def tab5_range(x0, x1):
    return sorted((tab5_u(x0), tab5_u(x1)))


# Local (u, v, w) -> global (X, Y, Z)
FACE = np.array([[1, 0, 0, 0], [0, C, -S, A[0]], [0, S, C, A[1]]], dtype=float)
# CrossSection drawn in (Y, Z), or in (v, w), and extruded along its z -> X / u
SIDE_VIEW = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]], dtype=float)


def compose(a, b):
    """3x4 affine a applied after b."""
    return np.hstack([a[:, :3] @ b[:, :3], (a[:, :3] @ b[:, 3] + a[:, 3])[:, None]])


def shift(x=0.0, y=0.0, z=0.0):
    return np.array([[1, 0, 0, x], [0, 1, 0, y], [0, 0, 1, z]], dtype=float)


def side_prism(cs, x0, x1):
    """Extrude a (Y, Z) cross-section along X from x0 to x1."""
    return cs.extrude(x1 - x0).transform(compose(shift(x=x0), SIDE_VIEW))


def face_cut(cs_uv, w0, w1):
    """Extrude a (u, v) cross-section along w from w0 to w1, placed on the slope."""
    return cs_uv.extrude(w1 - w0).transform(compose(FACE, shift(z=w0)))


def slope_prism(cs_vw, u0, u1):
    """Extrude a (v, w) cross-section along u from u0 to u1, placed on the slope."""
    return cs_vw.extrude(u1 - u0).transform(compose(FACE, compose(shift(x=u0), SIDE_VIEW)))


def face_hole(cs_uv, w_surface, depth):
    """Convex (u, v) outline on a sloped surface, swept straight down through the wall.

    Cutting vertically instead of square to the slope makes the hole's upper edge a
    vertical surface, so it prints without bridging or support.
    """
    pts = np.vstack(cs_uv.to_polygons())
    top = np.column_stack([pts, np.full(len(pts), w_surface + 1.0)]) @ FACE[:, :3].T + FACE[:, 3]
    return Manifold.hull_points(np.vstack([top, top - (0, 0, depth)]))


def rounded_rect(x0, y0, x1, y1, r):
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    return CrossSection.square((x1 - x0 - 2 * r, y1 - y0 - 2 * r)).translate(
        (x0 + r, y0 + r)).offset(r, JoinType.Round)


def ccw(points):
    pts = np.asarray(points, dtype=float)
    area = np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1])
    return pts if area > 0 else pts[::-1]


def band(v0, v1, w0, w1):
    """(Y, Z) cross-section of the slope band v0..v1 x w0..w1."""
    return CrossSection([ccw([vw(v0, w0), vw(v1, w0), vw(v1, w1), vw(v0, w1)])])


def neo_outline(clear=0.0):
    right = np.array(NEO_OUTLINE_RIGHT)
    left = right[-2:0:-1] * (-1, 1)
    outline = CrossSection([ccw(np.vstack([right, left]))])
    return outline.offset(clear, JoinType.Round) if clear else outline


def battery_range():
    x0, _, x1, _ = TAB5_BATTERY
    u0, u1 = tab5_range(x0, x1)
    return u0 - BATTERY_CLEAR, u1 + BATTERY_CLEAR


def side_profile(bottom=0.0):
    """Outer side profile in (Y, Z). `bottom` lets the rounding pass extend it below Z=0."""
    face_bottom = vw(-CLEAR - BOTTOM, 0)
    face_top = vw(V_TOP, 0)
    top_back = (face_top[0] + TOP_DEPTH, face_top[1])
    rear = (top_back[0] + REAR_LEAN, bottom)
    return ccw([(face_bottom[0], bottom), rear, top_back, face_top, face_bottom])


def outer_body():
    shrunk = CrossSection([side_profile(bottom=-2 * EDGE_R)]).offset(-EDGE_R, JoinType.Miter)
    core = side_prism(shrunk, -WIDTH / 2 + EDGE_R, WIDTH / 2 - EDGE_R)
    rounded = core.minkowski_sum(Manifold.sphere(EDGE_R, 24))
    return rounded.trim_by_plane((0, 0, 1), 0.0)


def cavity():
    """Hollow interior behind the solid frame that holds the slots.

    The frame is a slab parallel to the face: deep enough for the Neo up to the Tab5's
    battery notch, then just deep enough for the Tab5 and its plug channel, plus walls
    around the battery notch. Its back faces lean 30° off vertical and its steps face
    up, so the interior prints without support.
    """
    inner = CrossSection([side_profile()]).offset(-WALL, JoinType.Miter)
    inner = inner ^ CrossSection.square((1000, 1000)).translate((-500, FLOOR))
    lower = band(-500, LOWER_TOP, -LOWER_DEPTH, 500)
    upper = band(-500, 500, -UPPER_DEPTH, 500)
    hollow = side_prism(inner - lower - upper, -WIDTH / 2 + WALL, WIDTH / 2 - WALL)
    # Walls around the battery notch; 1 mm deeper than the lower frame so the two back
    # faces never coincide.
    n0, n1 = battery_range()
    return hollow - side_prism(band(-500, 500, -LOWER_DEPTH - 1, 500), n0 - WALL, n1 + WALL)


def neo_grips():
    """Finger scoops on both sides of the Neo slot, to lift it straight out."""
    half, depth = NEO_GRIP
    radius = 18.0
    vc, reach = NEO_H / 2, depth + 1
    # The upper end leans into the scoop as it gets deeper, so it prints without support.
    section = CrossSection([ccw([(vc - half, -reach), (vc + half - reach * RUN_PER_RISE, -reach),
                                 (vc + half, 0), (vc + half, 2), (vc - half, 2)])])
    along_v = np.array([[1, 0, 0, 0], [0, 0, 1, vc - half - 1], [0, -1, 0, 0]], dtype=float)
    grips = []
    for side in (-1, 1):
        edge = side * (NEO_W / 2 + CLEAR)
        u0, u1 = sorted((edge - side * 2, edge + side * radius))
        scoop = Manifold.cylinder(2 * half + 2, radius).transform(along_v)
        scoop = scoop.translate((edge, 0, radius - depth))
        grips.append(scoop.transform(FACE) ^ slope_prism(section, u0, u1))
    return grips


def cutouts():
    cuts = []
    # Neo: slot cut to its outline, flush with the face, a cable hole in its floor and
    # finger scoops at the sides.
    cuts.append(face_cut(neo_outline(CLEAR), -NEO_T, 5))
    hw, hh = NEO_HOLE
    hole = rounded_rect(-hw / 2, NEO_CABLE_V - hh / 2, hw / 2, NEO_CABLE_V + hh / 2, 8)
    cuts.append(face_hole(hole, -NEO_T, depth=2 * (LOWER_DEPTH - NEO_T) + 6))
    cuts += neo_grips()

    # Tab5: slot open at the top, so it slides in from above.
    u0, u1 = tab5_range(0, TAB5_W)
    cuts.append(face_cut(rounded_rect(u0 - CLEAR, V_TAB, u1 + CLEAR, V_TOP + 80, TAB5_R + CLEAR),
                         -TAB5_T, 5))
    # NP-F550 notch behind it, open at the top as well.
    n0, n1 = battery_range()
    cuts.append(face_cut(rounded_rect(n0, LOWER_TOP - 2, n1, V_TOP + 80, 3),
                         BATTERY_W, -TAB5_T + 0.1))
    # Speaker port: the grille on the Tab5's bottom edge vents forward through the face.
    s0, s1 = tab5_range(*TAB5_SPEAKER_X)
    grille_back = -TAB5_T + TAB5_SPEAKER_DEPTH[0] - 1.0
    cuts.append(face_cut(rounded_rect(s0 - 1, V_TAB - SPEAKER_PORT, s1 + 1, V_TAB + 2, 2),
                         grille_back, 5))

    # Hidden channel for the 90° USB-C plug, beside the slot and under the face, and the
    # slot its cable slides down into the hollow body. Both open at the top.
    edge = tab5_u(0) + (CLEAR if TAB5_MIRROR else -CLEAR)
    out = 1 if TAB5_MIRROR else -1
    reach = PLUG[0] + 1.5
    a, b = sorted((edge - out * 1.5, edge + out * reach))  # runs 1.5 mm under the Tab5 edge
    vc = V_TAB + TAB5_USBC_Y
    cuts.append(face_cut(rounded_rect(a, vc - PLUG[1] / 2 - PLUG_CLEAR, b, V_TOP + 80, 1),
                         *CHANNEL))
    uc = edge + out * (PLUG[0] - 3.0)
    cuts.append(face_cut(rounded_rect(uc - CABLE_SLOT / 2, vc - CABLE_SLOT / 2,
                                      uc + CABLE_SLOT / 2, V_TOP + 80, CABLE_SLOT / 2),
                         -UPPER_DEPTH - 3, CHANNEL[0] + 0.1))

    # Cable exit at the bottom of the back wall, with a 45° chamfered top.
    ew, eh = REAR_EXIT
    rear_y = side_profile()[:, 0].max()
    c = ew / 2 - 8
    arch = CrossSection([ccw([(-ew / 2, -5), (ew / 2, -5), (ew / 2, eh - c), (ew / 2 - c, eh),
                              (c - ew / 2, eh), (-ew / 2, eh - c)])])
    cuts.append(arch.extrude(14).transform(
        compose(shift(y=rear_y + 2), np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0]], float))))

    # Recesses for rubber feet.
    profile = side_profile()
    y_front, y_back = profile[:, 0].min(), profile[:, 0].max()
    for x in (-WIDTH / 2 + FOOT_INSET, WIDTH / 2 - FOOT_INSET):
        for y in (y_front + FOOT_INSET, y_back - FOOT_INSET):
            cuts.append(Manifold.cylinder(FOOT_DEPTH + 1, FOOT_D / 2).translate((x, y, -1)))
    return Manifold.batch_boolean(cuts, OpType.Add)


def build():
    return outer_body() - cavity() - cutouts()


def write_stl(manifold, path):
    mesh = manifold.to_mesh()
    verts = np.asarray(mesh.vert_properties, dtype=np.float32)[:, :3]
    tris = verts[np.asarray(mesh.tri_verts)]
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12
    record = np.zeros(len(tris), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    record["n"], record["v"] = normals, tris
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"Tab5 + Stream Deck Neo stand".ljust(80, b" "))
        f.write(np.uint32(len(tris)).tobytes())
        f.write(record.tobytes())


def main():
    stand = build()
    write_stl(stand, OUT)
    (x0, y0, z0), (x1, y1, z1) = np.array(stand.bounding_box()).reshape(2, 3)
    print(f"{OUT.relative_to(Path(__file__).parent)}: {x1 - x0:.1f} x {y1 - y0:.1f} x "
          f"{z1 - z0:.1f} mm, {stand.volume() / 1000:.0f} cm3, {stand.num_tri()} triangles, "
          f"genus {stand.genus()}")


if __name__ == "__main__":
    main()
