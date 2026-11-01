"""Device mock-ups placed on the stand, shared by the fit check and the preview renders."""

import sys
import urllib.request
from pathlib import Path

import numpy as np
from manifold3d import CrossSection, Manifold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import generate_stand as g  # noqa: E402

# Official Tab5 model from M5Stack. It is downloaded on demand and never committed.
TAB5_STL_URL = ("https://raw.githubusercontent.com/m5stack/M5_Hardware/master/"
                "Products/C145_Tab5/Structures/Tab5.stl")
TAB5_STL_CACHE = ROOT / ".cache" / "Tab5.stl"

CABLE_D = 4.5


def on_face(local):
    """Manifold built in (u, v, w) -> global stand coordinates."""
    return local.transform(g.FACE)


def box(u0, u1, v0, v1, w0, w1, r=0.0):
    section = g.rounded_rect(u0, v0, u1, v1, r) if r else \
        CrossSection.square((u1 - u0, v1 - v0)).translate((u0, v0))
    return g.face_cut(section, w0, w1)


def tab5():
    u0, u1 = g.tab5_range(0, g.TAB5_W)
    return box(u0, u1, g.V_TAB, g.V_TOP, -g.TAB5_T, 0, r=g.TAB5_R)


def battery():
    x0, y0, x1, y1 = g.TAB5_BATTERY
    u0, u1 = g.tab5_range(x0, x1)
    w0 = -g.TAB5_T - g.TAB5_BATTERY_PROTRUSION
    return box(u0, u1, g.V_TAB + y0, g.V_TAB + y1, w0, -g.TAB5_T)


def usb_plug_head():
    edge = g.tab5_u(0)
    out = 1 if g.TAB5_MIRROR else -1
    length, width, thick = g.PLUG
    v = g.V_TAB + g.TAB5_USBC_Y
    return box(*sorted((edge, edge + out * length)), v - width / 2, v + width / 2,
               g.PLUG_W - thick / 2, g.PLUG_W + thick / 2)


def usb_plug():
    """90° USB-C plug on the Tab5's left edge, its cable heading back into the stand."""
    edge = g.tab5_u(0)
    out = 1 if g.TAB5_MIRROR else -1
    u_cable = edge + out * (g.PLUG[0] - CABLE_D / 2 - 1)
    v = g.V_TAB + g.TAB5_USBC_Y
    w_end = -g.UPPER_DEPTH - 10  # well inside the hollow body
    cable = on_face(Manifold.cylinder(g.PLUG_W - w_end, CABLE_D / 2)
                    .translate((u_cable, v, w_end)))
    return usb_plug_head() + cable


def neo():
    return g.face_cut(g.neo_outline(), -g.NEO_T, 0)


def neo_cable():
    """Neo's captive cable leaving the middle of its back, straight into the stand."""
    return on_face(Manifold.cylinder(15, CABLE_D / 2)
                   .translate((0, g.NEO_CABLE_V, -g.NEO_T - 15)))


def in_front(outline_uv):
    """Everything in front of the face within a device outline (must stay empty)."""
    return g.face_cut(outline_uv, 0.01, 200)


def tab5_outline():
    u0, u1 = g.tab5_range(0, g.TAB5_W)
    return g.rounded_rect(u0, g.V_TAB, u1, g.V_TOP, g.TAB5_R)


def speaker_path():
    """Air from the speaker grille down into the channel and out of the side (must stay empty)."""
    u0, u1 = g.tab5_range(*g.TAB5_SPEAKER_X)
    back, front = (-g.TAB5_T + d for d in g.TAB5_SPEAKER_DEPTH)
    down = box(u0, u1, g.DUCT_ROOF, g.V_TAB, back, front)
    along = box(*sorted((u1 if g.PLUG_SIDE < 0 else u0, -g.PLUG_SIDE * (g.WIDTH / 2 + 1))),
                g.DUCT_FLOOR + 0.5, g.DUCT_FLOOR + 3, back, front)
    return down + along


def speaker_cover():
    """Face material in front of the speaker channel (must be fully solid: no front port)."""
    u0, u1 = g.tab5_range(*g.TAB5_SPEAKER_X)
    a, b = sorted((u0 - 1 if g.PLUG_SIDE < 0 else u1 + 1, -g.PLUG_SIDE * (g.WIDTH / 2 - 3)))
    return box(a, b, g.DUCT_FLOOR, g.V_TAB - g.CLEAR - 0.1, g.DUCT_W[1] + 0.2, -0.2)


def plug_cover():
    """Face material directly in front of the USB-C plug (must be fully solid)."""
    edge = g.tab5_u(0) + (g.CLEAR if g.TAB5_MIRROR else -g.CLEAR)
    out = 1 if g.TAB5_MIRROR else -1
    v = g.V_TAB + g.TAB5_USBC_Y
    width = g.PLUG[1]
    return box(*sorted((edge, edge + out * g.PLUG[0])), v - width / 2, v + width / 2,
               g.CHANNEL_W[1] + 0.2, -0.2)


FACE_INV = np.hstack([g.FACE[:, :3].T, (-g.FACE[:, :3].T @ g.FACE[:, 3])[:, None]])


def moved(part, local_motion):
    """Apply a local (u, v, w) motion, such as g.tab5_motion(), to a global part."""
    return part.transform(g.compose(g.FACE, g.compose(local_motion, FACE_INV)))


def moved_points(points, local_motion):
    m = g.compose(g.FACE, g.compose(local_motion, FACE_INV))
    return points @ m[:, :3].T + m[:, 3]


def tab5_removal_path(steps=8):
    """(phase, local motion) samples along the Tab5's way out of its slot."""
    path = [("tilt", g.tab5_motion(t)) for t in np.linspace(0, g.TAB5_TILT_IN, steps + 1)]
    path += [("slide", g.tab5_motion(g.TAB5_TILT_IN, s))
             for s in np.linspace(0, g.TAB5_SLIDE, steps + 1)[1:]]
    path += [("lift", g.tab5_motion(g.TAB5_TILT_IN, g.TAB5_SLIDE, lift))
             for lift in np.linspace(0, 30, steps + 1)[1:]]
    return path


def read_stl(path):
    data = Path(path).read_bytes()
    count = int(np.frombuffer(data, "<u4", 1, 80)[0])
    if 84 + 50 * count == len(data):
        rec = np.frombuffer(data, [("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")], count, 84)
        return rec["v"].astype(float)
    nums = [line.split()[1:] for line in data.decode().splitlines() if line.strip().startswith("vertex")]
    return np.array(nums, dtype=float).reshape(-1, 3, 3)


def tab5_reference_triangles():
    """Official Tab5 model on the stand, as a triangle soup (for renders only)."""
    if not TAB5_STL_CACHE.exists():
        TAB5_STL_CACHE.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(TAB5_STL_URL, TAB5_STL_CACHE)
    tris = read_stl(TAB5_STL_CACHE)
    # The file also holds an exploded view at negative Y; keep the assembled unit.
    tris = tris[tris[:, :, 1].mean(axis=1) > 0]
    x, y, z = tris[..., 0], tris[..., 1] - 0.9, tris[..., 2]  # screen at z = 0, back at z = -12
    u = np.vectorize(g.tab5_u)(x)
    local = np.stack([u, g.V_TAB + y, z], axis=-1)
    out = local @ g.FACE[:, :3].T + g.FACE[:, 3]
    return out[:, ::-1] if g.TAB5_MIRROR else out


def manifold_triangles(m):
    mesh = m.to_mesh()
    verts = np.asarray(mesh.vert_properties)[:, :3]
    return verts[np.asarray(mesh.tri_verts)]
