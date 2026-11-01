"""Straight-line, chamfered lettering for the face livery (mech-style markings).

Glyphs are centre lines on a grid 6 units tall and up to 4 wide. text() strokes them
with mitred joins and square ends and clips each glyph to its cell, so stroke ends that
meet another stroke stay hidden inside it.
"""

import numpy as np
from manifold3d import CrossSection, FillRule, OpType

CAP = 6.0  # grid units from baseline to cap line

# Polylines in grid units; a polyline whose last point repeats the first is closed.
GLYPHS = {
    " ": (3, []),
    "-": (3, [[(0, 3), (3, 3)]]),
    "/": (3, [[(0, 0), (3, 6)]]),
    "0": (4, [[(1, 0), (4, 0), (4, 5), (3, 6), (0, 6), (0, 1), (1, 0)]]),
    "5": (4, [[(4, 6), (0, 6), (0, 3), (3, 3), (4, 2), (4, 1), (3, 0), (0, 0)]]),
    "6": (4, [[(4, 6), (1, 6), (0, 5), (0, 0), (4, 0), (4, 3), (0, 3)]]),
    "A": (4, [[(0, 0), (0, 5), (1, 6), (3, 6), (4, 5), (4, 0)], [(0, 2.5), (4, 2.5)]]),
    "C": (4, [[(4, 6), (1, 6), (0, 5), (0, 1), (1, 0), (4, 0)]]),
    "D": (4, [[(0, 0), (3, 0), (4, 1), (4, 5), (3, 6), (0, 6), (0, 0)]]),
    "E": (4, [[(4, 6), (0, 6), (0, 0), (4, 0)], [(0, 3), (3, 3)]]),
    "I": (0, [[(0, 0), (0, 6)]]),
    "K": (4, [[(0, 0), (0, 6)], [(4, 6), (1, 3), (4, 0)], [(0, 3), (1, 3)]]),
    "L": (4, [[(0, 6), (0, 0), (4, 0)]]),
    "N": (4, [[(0, 0), (0, 6), (4, 0), (4, 6)]]),
    "O": (4, [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)]]),
    "R": (4, [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)], [(3, 3), (4, 2), (4, 0)]]),
    "S": (4, [[(4, 6), (1, 6), (0, 5), (0, 4), (1, 3), (3, 3), (4, 2), (4, 1), (3, 0), (0, 0)]]),
    "T": (4, [[(0, 6), (4, 6)], [(2, 6), (2, 0)]]),
    "U": (4, [[(0, 6), (0, 1), (1, 0), (3, 0), (4, 1), (4, 6)]]),
}


def stroke(points, width):
    """Polyline -> CrossSection of the given width, with mitred joins and square ends."""
    p = np.asarray(points, dtype=float)
    closed = len(p) > 2 and np.allclose(p[0], p[-1])
    if closed:
        p = p[:-1]
    h = width / 2
    seg = np.roll(p, -1, axis=0) - p if closed else np.diff(p, axis=0)
    d = seg / np.linalg.norm(seg, axis=1, keepdims=True)
    n = np.column_stack([-d[:, 1], d[:, 0]])

    def offset(sign):
        out = []
        if not closed:
            out.append(p[0] + h * (sign * n[0] - d[0]))
        joints = range(len(p)) if closed else range(1, len(p) - 1)
        for j in joints:
            a, b = n[j - 1], n[j]
            out.append(p[j] + sign * h * (a + b) / (1 + a @ b))
        if not closed:
            out.append(p[-1] + h * (sign * n[-1] + d[-1]))
        return np.array(out)

    left, right = offset(1), offset(-1)
    if closed:  # outer loop counter-clockwise, inner loop clockwise
        loops = sorted((left, right), key=lambda c: -abs(_area(c)))
        return CrossSection([_oriented(loops[0], 1), _oriented(loops[1], -1)], FillRule.Positive)
    return CrossSection([_oriented(np.vstack([left, right[::-1]]), 1)], FillRule.Positive)


def _area(c):
    return 0.5 * np.sum(c[:, 0] * np.roll(c[:, 1], -1) - np.roll(c[:, 0], -1) * c[:, 1])


def _oriented(c, sign):
    return c if np.sign(_area(c)) == sign else c[::-1]


def advance(char, height, width, spacing):
    unit = (height - width) / CAP
    return GLYPHS[char][0] * unit + width + spacing


def text_width(s, height, width, spacing=None):
    spacing = width if spacing is None else spacing
    return sum(advance(c, height, width, spacing) for c in s) - spacing


def text(s, x, y, height, width, spacing=None):
    """Text with its bottom-left corner at (x, y); `height` is the cap height, outside
    the strokes."""
    spacing = width if spacing is None else spacing
    unit = (height - width) / CAP
    h = width / 2
    out = CrossSection()
    for char in s:
        cols, lines = GLYPHS[char]
        if lines:
            glyph = CrossSection.batch_boolean(
                [stroke(np.asarray(line, dtype=float) * unit + (h, h), width) for line in lines],
                OpType.Add)
            cell = CrossSection.square((cols * unit + width, height))
            out += (glyph ^ cell).translate((x, y))
        x += advance(char, height, width, spacing)
    return out
