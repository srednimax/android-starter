"""The placeholder mark: the single definition of this app's identity.

**Replace this file.** It draws a rounded triangle with a hole punched through it — deliberately
generic, deliberately obviously a placeholder. Both generators import it (`make-launcher-icon.py`
emits it as `VectorDrawable` path data, `make-feature-graphic.py` rasterises it with PIL), so
whatever you put here cannot drift into being two different marks.

The way to replace it: draw or generate a concept image, run `python3 art/trace-mark.py <image>`,
and paste the curves it prints over MARK and EYE below. Nothing else in the pipeline changes.

**Use art you have the right to ship.** An icon traced from an emoji font, a stock icon or someone
else's mark is a licence obligation at best and a rejected Play upload at worst. Art you generated
from your own prompt, or drew, is clean.

The geometry is two subpaths: the shape, and the hole punched out of it. Coordinates are in
arbitrary units around an origin at the mark's centre; callers fit them to their own canvas with
`fit()`. y grows downward, as it does in both SVG and PIL.
"""

import re
from dataclasses import dataclass

# The identity's colours. The mark is near-white, so the ground carries all the colour: recolouring
# means PRIMARY here *and* the matching fillColor in res/drawable/ic_launcher_background.xml, which
# make-launcher-icon.py deliberately does not write. Changing one alone is the failure to expect.
SURFACE = (0xFF, 0xFB, 0xFF)  # the light scheme's `surface`
PRIMARY = (0x2B, 0x4C, 0x7E)  # `primary`, darkened for contrast against SURFACE at icon sizes
PRIMARY_DARK = (0x14, 0x25, 0x3F)  # second stop of the feature graphic's gradient


@dataclass(frozen=True)
class Subpath:
    """One closed contour, as cubic path data.

    `d` is always wound CLOCKWISE on screen (positive shoelace area with y downward). A hole is
    stored the same way and reversed at read time by `nodes()`, so it is subtracted by the non-zero
    fill rule that both SVG and VectorDrawable use by default. That is what makes the hole a real
    hole rather than a shape painted in the background colour — and it is why it survives the
    monochrome layer, where Android tints everything one flat colour and a painted hole would vanish.
    """

    d: str
    hole: bool = False


# A rounded triangle pointing right. One outer contour.
MARK = (
    "M-27.48,-73.6"
        "C-39.92,-80.78 -50,-74.96 -50,-60.6C-50,-20.2 -50,20.2 -50,60.6"
        "C-50,74.96 -39.92,80.78 -27.48,73.6C7.51,53.4 42.49,33.2 77.48,13"
        "C89.92,5.82 89.92,-5.82 77.48,-13C42.49,-33.2 7.51,-53.4 -27.48,-73.6"
        "Z"
)

# The hole punched through it.
EYE = (
    "M20,0"
        "C20,14.36 8.36,26 -6,26C-20.36,26 -32,14.36 -32,0"
        "C-32,-14.36 -20.36,-26 -6,-26C8.36,-26 20,-14.36 20,0"
        "Z"
)

PARTS = (
    Subpath(MARK),
    Subpath(EYE, hole=True),
)

_NUM = re.compile(r"-?\d*\.?\d+(?:e-?\d+)?")


def _points(d):
    """Path data -> the flat control-point list: 1 start point plus 3 per cubic segment."""
    pts = []
    for chunk in re.finditer(r"[MC]([^MCZz]*)", d):
        nums = [float(v) for v in _NUM.findall(chunk.group(1))]
        pts += list(zip(nums[0::2], nums[1::2]))
    return pts


def nodes(e, tf=lambda p: p):
    """Control points, caller-transformed, wound for fill or hole."""
    pts = _points(e.d)
    if e.hole:
        pts.reverse()
    return [tf(p) for p in pts]


def path_data(e, tf=lambda p: p, precision=2):
    """SVG/VectorDrawable path data for one subpath."""
    n = nodes(e, tf)

    def f(p):
        return f"{round(p[0], precision):g},{round(p[1], precision):g}"

    out = [f"M{f(n[0])}"]
    for i in range(1, len(n), 3):
        out.append("C" + " ".join(f(n[i + j]) for j in range(3)))
    return "".join(out) + "Z"


def outline(e, tf=lambda p: p, steps=32):
    """The same subpath flattened to a polygon, for renderers that can't draw curves."""
    n = nodes(e, tf)
    pts = []
    for i in range(1, len(n), 3):
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = n[i - 1], n[i], n[i + 1], n[i + 2]
        for s in range(steps):
            t = s / steps
            u = 1 - t
            pts.append((
                u * u * u * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x3,
                u * u * u * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * y3,
            ))
    return pts


def bounds(parts=PARTS):
    """Bounding box of the silhouette. Holes are ignored — a hole cannot extend the mark."""
    xs, ys = [], []
    for e in parts:
        if e.hole:
            continue
        for x, y in outline(e):
            xs.append(x)
            ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def fit(canvas, art_size, parts=PARTS):
    """A transform placing the mark centred on a square canvas at a given longest-side size.

    Returns a function mapping mark coordinates to canvas coordinates.
    """
    x0, y0, x1, y1 = bounds(parts)
    scale = art_size / max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return lambda p: (canvas / 2 + (p[0] - cx) * scale, canvas / 2 + (p[1] - cy) * scale)
