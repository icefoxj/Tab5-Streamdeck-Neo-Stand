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

PLUG_LEN, PLUG_W, PLUG_T, CABLE_D = 13.0, 13.0, 7.0, 4.5  # generous 90° USB-C plug


def on_face(local):
    """Manifold built in (u, v, w) -> global stand coordinates."""
    return local.transform(g.FACE)


def box(u0, u1, v0, v1, w0, w1, r=0.0):
    section = g.rounded_rect(u0, v0, u1, v1, r) if r else \
        CrossSection.square((u1 - u0, v1 - v0)).translate((u0, v0))
    return on_face(section.extrude(w1 - w0).translate((0, 0, w0)))


def tab5_x_range(x0, x1):
    return sorted((g.tab5_u(x0), g.tab5_u(x1)))


def tab5():
    u0, u1 = tab5_x_range(0, g.TAB5_W)
    return box(u0, u1, g.V_TAB, g.V_TOP, g.STEP, g.STEP + g.TAB5_T, r=4.0)


def battery():
    x0, y0, x1, y1 = g.TAB5_BATTERY
    u0, u1 = tab5_x_range(x0, x1)
    return box(u0, u1, g.V_TAB + y0, g.V_TAB + y1, g.STEP - g.TAB5_BATTERY_PROTRUSION, g.STEP)


def usb_plug():
    """90° USB-C plug on the Tab5's left edge with its cable heading into the stand."""
    edge = g.tab5_u(0)
    out = 1 if g.TAB5_MIRROR else -1
    u_far = edge + out * PLUG_LEN
    v = g.V_TAB + g.TAB5_USBC_Y
    w = g.STEP + g.TAB5_USBC_DEPTH
    head = box(*sorted((edge, u_far)), v - PLUG_W / 2, v + PLUG_W / 2, w - PLUG_T / 2, w + PLUG_T / 2)
    u_cable = edge + out * (PLUG_LEN - CABLE_D / 2 - 1)
    cable = on_face(Manifold.cylinder(w + 20, CABLE_D / 2).translate((u_cable, v, -20)))
    return head + cable


def neo():
    return box(-g.NEO_W / 2, g.NEO_W / 2, 0, g.NEO_H, 0, g.NEO_T, r=8.0)


def neo_cable():
    """Neo's captive cable leaving the middle of its back, straight into the stand."""
    return on_face(Manifold.cylinder(25, CABLE_D / 2).translate((0, g.NEO_H / 2, -25)))


def front_projection(u0, u1, v0, v1, w_back):
    """Everything in front of a device's back plane within its outline (must stay empty)."""
    return box(u0, u1, v0, v1, w_back + 0.01, 200)


def speaker_path():
    """Air between the speaker grille and the Neo's top edge (must stay empty)."""
    u0, u1 = tab5_x_range(*g.TAB5_SPEAKER_X)
    return box(u0, u1, g.NEO_H + 0.5, g.V_TAB - 0.01, g.STEP + 1.5, g.STEP + 7.5)


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
    local = np.stack([u, g.V_TAB + y, g.STEP + g.TAB5_T + z], axis=-1)
    out = local @ g.FACE[:, :3].T + g.FACE[:, 3]
    return out[:, ::-1] if g.TAB5_MIRROR else out


def manifold_triangles(m):
    mesh = m.to_mesh()
    verts = np.asarray(mesh.vert_properties)[:, :3]
    return verts[np.asarray(mesh.tri_verts)]
