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
STAND = "#3a3c41"     # black filament, lifted a little so the shading shows
ORNAMENT = "#f5c400"  # the livery, in yellow filament
DARK = "#202226"
GLASS = "#0d1b2a"
KEY = "#3a3f47"


def neo_mockup():
    """Neo body (real outline) with its 2 x 4 LCD keys and info bar, as in Elgato's render."""
    parts = [(d.neo(), "#e9eaec")]
    for v in (36.8, 56.0):
        for u in (-29.4, -9.8, 9.7, 29.2):
            parts.append((d.box(u - 8.3, u + 8.3, v - 8.3, v + 8.3, -0.5, 0.6, r=2.5), KEY))
    parts.append((d.box(-17.9, 17.9, 16.4, 24.5, -0.5, 0.4, r=1.5), GLASS))
    return [(d.manifold_triangles(m), c) for m, c in parts]


def tab5_mockup(motion=None):
    """Tab5 (official model, glass, screen), battery and 90° plug, optionally moved."""
    motion = g.tab5_motion() if motion is None else motion
    u0, u1 = g.tab5_range(0, g.TAB5_W)
    glass = d.box(u0, u1, g.V_TAB, g.V_TOP, -0.3, 0.05, r=g.TAB5_R)
    screen = d.box(u0 + 9, u1 - 9, g.V_TAB + 9, g.V_TOP - 9, 0, 0.15)
    parts = [(glass, DARK), (screen, "#24476b"), (d.battery(), "#55595f"),
             (d.usb_plug_head(), "#6b7078")]
    return ([(d.moved_points(d.tab5_reference_triangles(), motion), "#2b2e33")]
            + [(d.manifold_triangles(d.moved(m, motion)), c) for m, c in parts])


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
    body, inlay = g.build_parts()
    stand = [(d.manifold_triangles(body), STAND), (d.manifold_triangles(inlay), ORNAMENT)]
    devices = tab5_mockup() + neo_mockup()
    render(stand + devices, IMAGES / "stand_with_devices.png", elev=22, azim=-32)
    render(stand, IMAGES / "stand_front.png", elev=24, azim=-35)
    render(stand, IMAGES / "stand_back.png", elev=24, azim=145)
    render(stand + devices, IMAGES / "stand_side.png", elev=0, azim=-90, width=800)
    render(stand, IMAGES / "ornament.png", elev=90 - g.TILT, azim=0, width=900)
    # Speaker channel: the stand cut open 8 mm behind the face, seen square to the face.
    s0, s1 = g.tab5_range(*g.TAB5_SPEAKER_X)
    a, b = sorted((s0 - 12, -g.PLUG_SIDE * (g.WIDTH / 2 + 5)))
    window = d.box(a, b, g.NEO_TOP - 10, g.V_TAB + 12, -40, -8)
    grille = d.box(s0, s1, g.V_TAB, g.V_TAB + 1.5, -10, -6)
    render([(d.manifold_triangles(g.build() ^ window), STAND),
            (d.manifold_triangles(grille), "#3b6fb6")],
           IMAGES / "speaker_channel.png", elev=90 - g.TILT, azim=0, width=900)

    # How the Tab5 goes in: plug side first, hooked under the frame, then laid down.
    tilted = tab5_mockup(g.tab5_motion(g.TAB5_TILT_IN))
    render(stand + tilted + neo_mockup(), IMAGES / "tab5_insertion.png", elev=12, azim=62)


if __name__ == "__main__":
    main()
