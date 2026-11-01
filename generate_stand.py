"""Parametric desk stand for an M5Stack Tab5 (landscape) and an Elgato Stream Deck Neo.

    python generate_stand.py            -> writes stl/tab5_neo_stand.stl

All dimensions are in millimetres.

Output coordinates: X = width (left to right, seen from the front), Y = depth
(front to back), Z = up. The stand prints upright, exactly as it sits on the desk.

Features are placed in the frame of the inclined face:
    u  along X (0 = centre of the stand)
    v  up the slope (0 = bottom edge of the Neo)
    w  out of the slope, towards the user (0 = surface the Neo rests on)
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
TAB5_W, TAB5_H, TAB5_T = 128.0, 80.0, 12.0
TAB5_BATTERY = (81.2, 9.5, 119.4, 79.9)  # NP-F550 footprint on the back: x0, y0, x1, y1
TAB5_BATTERY_PROTRUSION = 14.7           # Tab5 Kit 26.7 mm - bare Tab5 12.0 mm
TAB5_SPEAKER_X = (91.5, 110.5)           # speaker grille on the bottom edge
TAB5_USBC_Y = 40.0                       # USB-C centre on the left edge
TAB5_USBC_DEPTH = 2.5                    # USB-C centre measured from the back face
TAB5_MIRROR = False                      # True if your USB-C ends up on the right side

# Elgato Stream Deck Neo with its integrated stand folded flat (official spec).
NEO_W, NEO_H, NEO_T = 107.0, 78.0, 26.0

# --------------------------------------------------------------------------
# Stand
# --------------------------------------------------------------------------
TILT = 60.0           # face angle from the desk
WALL = 2.4            # shell wall
FLOOR = 3.0           # bottom plate
EDGE_R = 1.6          # rounding of the outer edges
SIDE = 20.0           # face margin each side of the Tab5 (room for the 90° plug)
BASE_Z = 6.0          # height of the Neo's bottom-back corner above the desk
NEO_LIP = 8.0         # lip under the Neo (well below its 26 mm front face)
TAB5_GAP = 14.0       # Neo top edge -> Tab5 bottom edge; the speaker vents here
STEP = NEO_T - TAB5_T # Tab5 shelf is raised so both front faces are coplanar
TAB_H = 4.0           # support tabs: height above the shelf
TAB_T = 4.0           # support tabs: thickness along the slope
TAB_X = [(4.0, 14.0), (57.0, 71.0), (112.0, 124.0)]  # along the Tab5 bottom edge
TOP_DEPTH = 24.0      # flat top behind the Tab5
REAR_LEAN = 16.0      # rear foot sticks out this much further back than the top
MAX_OVERHANG = 40.0   # steepest printed overhang, degrees from vertical

BATTERY_CLEAR = 1.0   # each side of the battery notch (also centres the Tab5)
USB_SLOT_W = 17.0     # 90° USB-C plug pocket, measured outward from the Tab5 edge
USB_SLOT_L = 44.0     # pocket length along the Tab5 edge
NEO_HOLE = (44.0, 60.0, 10.0)   # cable hole behind the Neo: width, height, start v
REAR_EXIT = (56.0, 30.0)        # cable exit in the back wall: width, height
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
A = (0.0, BASE_Z)            # (Y, Z) of the Neo's bottom-back corner
V_TAB = NEO_H + TAB5_GAP     # bottom edge of the Tab5
V_TOP = V_TAB + TAB5_H       # top edge of the Tab5 = top of the stand
V_RISER = V_TAB - TAB_T      # top of the riser between the Neo face and the Tab5 shelf

set_circular_segments(64)


def vw(v, w):
    """(v, w) on the slope -> (Y, Z) in the side profile."""
    return (A[0] + v * C - w * S, A[1] + v * S + w * C)


def tab5_u(x):
    """Tab5 x (from its left edge) -> u on the stand."""
    return (TAB5_W / 2 - x) if TAB5_MIRROR else (x - TAB5_W / 2)


# Local (u, v, w) -> global (X, Y, Z)
FACE = np.array([[1, 0, 0, 0], [0, C, -S, A[0]], [0, S, C, A[1]]], dtype=float)
# CrossSection drawn in (Y, Z) and extruded along its z -> global, starting at X = x0
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


def face_hole(cs_uv, w_surface, depth=9.0):
    """Convex (u, v) outline on a slope surface, swept straight down through the wall.

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


def side_profile(bottom=0.0):
    """Outer side profile in (Y, Z). `bottom` lets the rounding pass extend it below Z=0."""
    toe = vw(0, NEO_LIP)
    riser_base = vw(V_RISER - STEP * RUN_PER_RISE, 0)
    riser_top = vw(V_RISER, STEP)
    top_front = vw(V_TOP, STEP)
    top_back = (top_front[0] + TOP_DEPTH, top_front[1])
    rear = (top_back[0] + REAR_LEAN, bottom)
    return ccw([(toe[0], bottom), rear, top_back, top_front, riser_top, riser_base, A, toe])


def outer_body():
    shrunk = CrossSection([side_profile(bottom=-2 * EDGE_R)]).offset(-EDGE_R, JoinType.Miter)
    core = side_prism(shrunk, -WIDTH / 2 + EDGE_R, WIDTH / 2 - EDGE_R)
    rounded = core.minkowski_sum(Manifold.sphere(EDGE_R, 24))
    return rounded.trim_by_plane((0, 0, 1), 0.0)


def cavity():
    inner = CrossSection([side_profile()]).offset(-WALL, JoinType.Miter)
    floor_cut = CrossSection.square((1000, 1000)).translate((-500, FLOOR))
    # Keep the toe solid so the lower face's inner skin runs straight to the floor
    # instead of leaving a small downward-facing pocket behind the lip.
    v_stop = V_RISER - STEP * RUN_PER_RISE - 2
    skin = -WALL - 0.2  # just behind the inner skin, so the two edges never coincide
    toe = CrossSection([ccw([vw(-200, skin), vw(v_stop, skin), vw(v_stop, 200), vw(-200, 200)])])
    pieces = ((inner ^ floor_cut) - toe).decompose()
    largest = max(pieces, key=lambda p: p.area())
    return side_prism(largest, -WIDTH / 2 + WALL, WIDTH / 2 - WALL)


def tab5_tabs():
    """Small tabs the Tab5's bottom edge sits on; they keep clear of the speaker grille."""
    rise = STEP + TAB_H
    base_v = V_RISER - rise * RUN_PER_RISE
    riser_dir = np.array([STEP * RUN_PER_RISE, STEP]) / np.hypot(STEP * RUN_PER_RISE, STEP)
    into_wall = np.array([riser_dir[1], -riser_dir[0]]) * 0.6  # sink 0.6 mm into the shell
    riser_base = np.array([V_RISER - STEP * RUN_PER_RISE, 0.0]) + into_wall
    # The underside runs on 0.5 mm into the face so it crosses it instead of touching it.
    section = [(base_v - 0.5 * RUN_PER_RISE, -0.5), (V_RISER, rise), (V_TAB, rise),
               (V_TAB, STEP - 0.6), tuple(riser_base), (base_v + 0.6, -0.6)]
    tabs = []
    for x0, x1 in TAB_X:
        u0, u1 = sorted((tab5_u(x0), tab5_u(x1)))
        pts = [FACE[:, :3] @ (u, v, w) + FACE[:, 3] for u in (u0, u1) for v, w in section]
        tabs.append(Manifold.hull_points(np.array(pts)))
    return Manifold.batch_boolean(tabs, OpType.Add)


def cutouts():
    cuts = []
    # Cable hole behind the Neo (its captive cable leaves the middle of its back).
    hw, hh, hv = NEO_HOLE
    cuts.append(face_hole(rounded_rect(-hw / 2, hv, hw / 2, hv + hh, 8), 0))

    # NP-F550 notch, open at the top so nothing has to bridge over it.
    x0, y0, x1, y1 = TAB5_BATTERY
    u0, u1 = sorted((tab5_u(x0), tab5_u(x1)))
    notch = rounded_rect(u0 - BATTERY_CLEAR, V_TAB + y0 - 2, u1 + BATTERY_CLEAR, V_TOP + 40, 3)
    cuts.append(face_cut(notch, STEP - TAB5_BATTERY_PROTRUSION - 1.5, STEP + 15))

    # Pocket for the 90° USB-C plug; its cable drops through into the hollow body.
    edge = tab5_u(0)
    out = -1 if not TAB5_MIRROR else 1
    ua, ub = sorted((edge - out * 1.5, edge + out * USB_SLOT_W))
    vc = V_TAB + TAB5_USBC_Y
    cuts.append(face_hole(rounded_rect(ua, vc - USB_SLOT_L / 2, ub, vc + USB_SLOT_L / 2, 6), STEP))

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
    body = outer_body() - cavity()
    body = body + tab5_tabs()
    return body - cutouts()


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
