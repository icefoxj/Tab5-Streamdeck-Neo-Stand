"""Renders the PNG previews in images/ (stand alone and with the devices on it).

    python tools/render_previews.py
"""

from math import cos, radians, sin

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import devices as d  # noqa: E402
from devices import g  # noqa: E402

IMAGES = d.ROOT / "images"
STAND = "#e8833a"
DARK = "#202226"
GLASS = "#0d1b2a"
KEY = "#3a3f47"


def neo_mockup():
    """Neo body with its 2 x 4 LCD keys and info bar, enough to read the layout."""
    parts = [(d.neo(), DARK)]
    key, pitch = 17.0, 22.0
    for row, v in enumerate((g.NEO_H - 30, g.NEO_H - 52)):
        for col in range(4):
            u = (col - 1.5) * pitch
            parts.append((d.box(u - key / 2, u + key / 2, v, v + key, g.NEO_T - 0.5, g.NEO_T + 0.6, r=2), KEY))
    parts.append((d.box(-30, 30, 8, 16, g.NEO_T - 0.5, g.NEO_T + 0.4, r=2), GLASS))
    return [(d.manifold_triangles(m), c) for m, c in parts]


def tab5_mockup():
    u0, u1 = d.tab5_x_range(0, g.TAB5_W)
    front = g.STEP + g.TAB5_T
    glass = d.box(u0, u1, g.V_TAB, g.V_TOP, front - 0.3, front + 0.05, r=4)
    screen = d.box(u0 + 9, u1 - 9, g.V_TAB + 9, g.V_TOP - 9, front, front + 0.15)
    return [(d.tab5_reference_triangles(), "#2b2e33"),
            (d.manifold_triangles(glass), DARK),
            (d.manifold_triangles(screen), "#24476b"),
            (d.manifold_triangles(d.battery()), "#55595f"),
            (d.manifold_triangles(d.usb_plug()), "#6b7078")]


def render(objects, path, elev, azim, width=1100, supersample=2):
    """Flat-shaded z-buffer render with outlines, saved as PNG."""
    e, a = radians(elev), radians(azim)
    view = np.array([cos(e) * sin(a), -cos(e) * cos(a), sin(e)])  # towards the camera
    right = np.cross((0, 0, 1), view)
    right /= np.linalg.norm(right)
    up = np.cross(view, right)
    light = view * 0.6 + up * 0.55 - right * 0.35
    light /= np.linalg.norm(light)

    tris = np.concatenate([t for t, _ in objects])
    rgb = np.concatenate([np.tile(matplotlib.colors.to_rgb(c), (len(t), 1)) for t, c in objects])
    ids = np.concatenate([np.full(len(t), i) for i, (t, _) in enumerate(objects)])
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    keep = n @ view > 1e-6
    tris, rgb, ids, n = tris[keep], rgb[keep], ids[keep], n[keep]
    shade = 0.38 + 0.62 * np.clip(n @ light, 0, 1)
    colors = np.clip(rgb * shade[:, None] + 0.03, 0, 1)

    xy = np.stack([tris @ right, -(tris @ up)], axis=-1)
    z = tris @ view
    lo, hi = xy.reshape(-1, 2).min(0), xy.reshape(-1, 2).max(0)
    w_px = width * supersample
    scale = (w_px - 40 * supersample) / (hi - lo)[0]
    h_px = int((hi - lo)[1] * scale) + 40 * supersample
    px = (xy - lo) * scale + 20 * supersample

    zbuf = np.full((h_px, w_px), -np.inf)
    image = np.ones((h_px, w_px, 3))
    normal = np.zeros((h_px, w_px, 3))
    obj = np.full((h_px, w_px), -1)
    for t in range(len(px)):
        (x0, y0), (x1, y1), (x2, y2) = px[t]
        xa, xb = int(max(min(x0, x1, x2), 0)), int(min(max(x0, x1, x2), w_px - 1)) + 1
        ya, yb = int(max(min(y0, y1, y2), 0)), int(min(max(y0, y1, y2), h_px - 1)) + 1
        if xa >= xb or ya >= yb:
            continue
        gx, gy = np.meshgrid(np.arange(xa, xb) + 0.5, np.arange(ya, yb) + 0.5)
        det = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(det) < 1e-12:
            continue
        l0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / det
        l1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / det
        l2 = 1 - l0 - l1
        inside = (l0 >= -1e-9) & (l1 >= -1e-9) & (l2 >= -1e-9)
        depth = l0 * z[t, 0] + l1 * z[t, 1] + l2 * z[t, 2]
        region = zbuf[ya:yb, xa:xb]
        win = inside & (depth > region)
        region[win] = depth[win]
        image[ya:yb, xa:xb][win] = colors[t]
        normal[ya:yb, xa:xb][win] = n[t]
        obj[ya:yb, xa:xb][win] = ids[t]

    # Outlines where the object, the depth or the surface direction jumps.
    edge = np.zeros((h_px, w_px), bool)
    for dy, dx in ((0, 1), (1, 0)):
        a_, b_ = (slice(None, -dy or None), slice(None, -dx or None)), (slice(dy, None), slice(dx, None))
        both = (obj[a_] >= 0) & (obj[b_] >= 0)
        jump = obj[a_] != obj[b_]
        dz = np.subtract(zbuf[a_], zbuf[b_], where=both, out=np.zeros(both.shape))
        jump |= both & (np.abs(dz) > 1.5)
        jump |= both & ((normal[a_] * normal[b_]).sum(-1) < cos(radians(40)))
        edge[a_] |= jump
    image[edge & (obj >= 0)] *= 0.35
    image[edge & (obj < 0)] = (0.2, 0.2, 0.2)

    ss, rows = supersample, h_px // supersample
    image = image[: rows * ss].reshape(rows, ss, w_px // ss, ss, 3).mean(axis=(1, 3))
    plt.imsave(path, image)
    print(f"wrote {path.relative_to(d.ROOT)}")


def main():
    IMAGES.mkdir(exist_ok=True)
    stand = [(d.manifold_triangles(g.build()), STAND)]
    devices = tab5_mockup() + neo_mockup()
    render(stand + devices, IMAGES / "stand_with_devices.png", elev=22, azim=-32)
    render(stand, IMAGES / "stand_front.png", elev=24, azim=-35)
    render(stand, IMAGES / "stand_back.png", elev=24, azim=145)
    render(stand + devices, IMAGES / "stand_side.png", elev=0, azim=-90, width=800)


if __name__ == "__main__":
    main()
