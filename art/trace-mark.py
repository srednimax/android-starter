"""Trace a two-colour raster mark into cubic Bezier path data.

Why not an off-the-shelf autotracer: those threshold to a binary bitmap first, so they
trace the pixel staircase and then have to smooth it back out — which is where wobbly
300-node paths come from. The source here is antialiased, and that antialiasing is
sub-pixel shape information. So:

  1. build a continuous 0..1 "insideness" field by projecting each pixel onto the
     cream->ground colour axis, keeping the antialiased edge as real data;
  2. marching squares at 0.5 with linear interpolation -> sub-pixel contours;
  3. Douglas-Peucker to drop redundant points;
  4. detect true corners, so a tapering wedge keeps its point instead of being rounded off;
  5. Schneider least-squares cubic fitting between corners.

Writes `path_outer.txt` and `path_eye.txt` next to the working directory and prints both.
Paste them into `mark.py`'s MARK and EYE. The paste is deliberate rather than automated:
`mark.py` is the single definition of the mark, and a definition a script rewrites on every
run is one nobody can hand-correct.

    python3 art/trace-mark.py concept.png

The source should be **two-tone and antialiased** — a light mark on a dark ground or the
reverse — at a few hundred pixels on its longest side. A photograph, a gradient or a
drop shadow will produce a contour that follows the shading rather than the shape.
"""
import argparse
import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

# The concept image, given on the command line. Defaults to `concept.png` beside this file.
SRC = str(Path(__file__).parent / 'concept.png')
CROP = (6, 6, 591, 592)          # the generator left a near-white frame on two edges
SURFACE = (254, 247, 237)
PRIMARY = (107, 50, 58)
BLUR = 1.0                       # px, kills sub-pixel edge ripple in the source
UNITS = 280                      # longest side of the emitted mark, in mark coordinates
DP_TOL = 0.55                    # px, Douglas-Peucker
CORNER_DEG = 125                 # interior angle below this is a corner, not a smooth join
FIT_TOL = 0.9                    # px, max deviation of a fitted cubic from the contour


# ---------------------------------------------------------------- field + contours

def insideness(blur=BLUR):
    im = Image.open(SRC).convert('RGB').crop(CROP)
    im = im.filter(ImageFilter.ModeFilter(3))
    if blur:
        # The source's straight edges ripple by a fraction of a pixel — a generation artifact,
        # not shape. Marching squares would trace it faithfully and it shows up as a ragged
        # "torn paper" edge along the mark's base at 512px. Blurring the field averages the
        # ripple out below the contour's own resolution; at this radius it costs ~0.2% of the
        # canvas at corners, which is far less than the wobble it removes.
        im = im.filter(ImageFilter.GaussianBlur(blur))
    W, H = im.size
    px = im.load()
    ax = tuple(SURFACE[i] - PRIMARY[i] for i in range(3))
    den = sum(c * c for c in ax)
    f = [[0.0] * H for _ in range(W)]
    for y in range(H):
        for x in range(W):
            c = px[x, y]
            t = sum((c[i] - PRIMARY[i]) * ax[i] for i in range(3)) / den
            f[x][y] = 0.0 if t < 0 else 1.0 if t > 1 else t
    return f, W, H


def marching_squares(f, W, H, iso=0.5):
    """Segments oriented so the inside (>= iso) lies to the LEFT of travel."""
    def ip(ax_, ay, av, bx, by, bv):
        t = (iso - av) / (bv - av) if bv != av else 0.5
        return (ax_ + (bx - ax_) * t, ay + (by - ay) * t)

    segs = []
    for y in range(H - 1):
        for x in range(W - 1):
            v0, v1, v2, v3 = f[x][y], f[x + 1][y], f[x + 1][y + 1], f[x][y + 1]
            idx = (v0 >= iso) | ((v1 >= iso) << 1) | ((v2 >= iso) << 2) | ((v3 >= iso) << 3)
            if idx in (0, 15):
                continue
            top = ip(x, y, v0, x + 1, y, v1)
            right = ip(x + 1, y, v1, x + 1, y + 1, v2)
            bottom = ip(x + 1, y + 1, v2, x, y + 1, v3)
            left = ip(x, y + 1, v3, x, y, v0)
            if idx == 5 or idx == 10:                      # saddle: resolve by cell average
                avg = (v0 + v1 + v2 + v3) / 4
                if idx == 5:
                    segs += [(left, top), (right, bottom)] if avg >= iso else [(left, bottom), (right, top)]
                else:
                    segs += [(top, right), (bottom, left)] if avg >= iso else [(top, left), (bottom, right)]
                continue
            table = {
                1: (left, top), 2: (top, right), 3: (left, right), 4: (right, bottom),
                6: (top, bottom), 7: (left, bottom), 8: (bottom, left), 9: (bottom, top),
                11: (bottom, right), 12: (right, left), 13: (right, top), 14: (top, left),
            }
            segs.append(table[idx])
    return segs


def chain(segs):
    """Join segments end-to-end into closed rings."""
    key = lambda p: (round(p[0], 4), round(p[1], 4))
    nxt = {}
    for a, b in segs:
        nxt.setdefault(key(a), []).append((a, b))
    rings, used = [], set()
    for i, (a0, b0) in enumerate(segs):
        if i in used:
            continue
        ring = [a0]
        cur, guard = (a0, b0), 0
        while True:
            used.add(segs.index(cur) if cur in segs else -1)
            ring.append(cur[1])
            cands = nxt.get(key(cur[1]), [])
            cands = [s for s in cands if s is not cur]
            if not cands or key(cur[1]) == key(a0) or guard > 4_000_000:
                break
            cur = cands[0]
            guard += 1
        if len(ring) > 8:
            rings.append(ring)
    return rings


# ---------------------------------------------------------------- simplify + corners

def rdp(pts, tol):
    if len(pts) < 3:
        return pts
    ax_, ay = pts[0]
    bx, by = pts[-1]
    dx, dy = bx - ax_, by - ay
    n = math.hypot(dx, dy)
    best, bi = -1.0, 0
    for i in range(1, len(pts) - 1):
        px_, py = pts[i]
        d = abs(dy * px_ - dx * py + bx * ay - by * ax_) / n if n else math.hypot(px_ - ax_, py - ay)
        if d > best:
            best, bi = d, i
    if best <= tol:
        return [pts[0], pts[-1]]
    return rdp(pts[:bi + 1], tol)[:-1] + rdp(pts[bi:], tol)


def corners(ring, deg):
    out = []
    n = len(ring)
    for i in range(n):
        a, b, c = ring[(i - 1) % n], ring[i], ring[(i + 1) % n]
        v1 = (a[0] - b[0], a[1] - b[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        n1, n2 = math.hypot(*v1), math.hypot(*v2)
        if n1 == 0 or n2 == 0:
            continue
        cosang = max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
        if math.degrees(math.acos(cosang)) < deg:
            out.append(i)
    return out


# ---------------------------------------------------------------- Schneider fitting

def sub(a, b): return (a[0] - b[0], a[1] - b[1])
def add(a, b): return (a[0] + b[0], a[1] + b[1])
def mul(a, s): return (a[0] * s, a[1] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1]


def norm(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n) if n else (0.0, 0.0)


def bez(c, t):
    u = 1 - t
    return add(add(mul(c[0], u ** 3), mul(c[1], 3 * u * u * t)),
               add(mul(c[2], 3 * u * t * t), mul(c[3], t ** 3)))


def chord_param(pts):
    u = [0.0]
    for i in range(1, len(pts)):
        u.append(u[-1] + math.hypot(*sub(pts[i], pts[i - 1])))
    return [x / u[-1] for x in u] if u[-1] else [0.0] * len(pts)


def gen_bezier(pts, u, t1, t2):
    n = len(pts)
    a = [(mul(t1, 3 * (1 - ui) ** 2 * ui), mul(t2, 3 * (1 - ui) * ui * ui)) for ui in u]
    c = [[0.0, 0.0], [0.0, 0.0]]
    x = [0.0, 0.0]
    for i in range(n):
        c[0][0] += dot(a[i][0], a[i][0]); c[0][1] += dot(a[i][0], a[i][1])
        c[1][0] = c[0][1];                c[1][1] += dot(a[i][1], a[i][1])
        ui = u[i]
        tmp = sub(pts[i], add(add(mul(pts[0], (1 - ui) ** 3), mul(pts[0], 3 * (1 - ui) ** 2 * ui)),
                              add(mul(pts[-1], 3 * (1 - ui) * ui * ui), mul(pts[-1], ui ** 3))))
        x[0] += dot(a[i][0], tmp); x[1] += dot(a[i][1], tmp)
    det = c[0][0] * c[1][1] - c[1][0] * c[0][1]
    a1 = (x[0] * c[1][1] - x[1] * c[0][1]) / det if det else 0.0
    a2 = (c[0][0] * x[1] - c[1][0] * x[0]) / det if det else 0.0
    seg = math.hypot(*sub(pts[-1], pts[0]))
    if a1 < 1e-6 or a2 < 1e-6:
        a1 = a2 = seg / 3
    return [pts[0], add(pts[0], mul(t1, a1)), add(pts[-1], mul(t2, a2)), pts[-1]]


def max_error(pts, u, c):
    worst, wi = 0.0, len(pts) // 2
    for i in range(1, len(pts) - 1):
        d = math.hypot(*sub(bez(c, u[i]), pts[i]))
        if d > worst:
            worst, wi = d, i
    return worst, wi


def reparam(pts, u, c):
    out = []
    for p, ui in zip(pts, u):
        d1 = [mul(sub(c[i + 1], c[i]), 3) for i in range(3)]
        d2 = [mul(sub(d1[i + 1], d1[i]), 2) for i in range(2)]
        uu = 1 - ui
        q1 = add(add(mul(d1[0], uu * uu), mul(d1[1], 2 * uu * ui)), mul(d1[2], ui * ui))
        q2 = add(mul(d2[0], uu), mul(d2[1], ui))
        diff = sub(bez(c, ui), p)
        den = dot(q1, q1) + dot(diff, q2)
        out.append(ui if den == 0 else ui - dot(diff, q1) / den)
    return out


def fit_cubic(pts, t1, t2, tol, depth=0):
    if len(pts) == 2:
        d = math.hypot(*sub(pts[1], pts[0])) / 3
        return [[pts[0], add(pts[0], mul(t1, d)), add(pts[1], mul(t2, d)), pts[1]]]
    u = chord_param(pts)
    c = gen_bezier(pts, u, t1, t2)
    err, split = max_error(pts, u, c)
    if err < tol:
        return [c]
    if err < tol * tol and depth < 24:
        for _ in range(12):
            u = reparam(pts, u, c)
            c = gen_bezier(pts, u, t1, t2)
            err, split = max_error(pts, u, c)
            if err < tol:
                return [c]
    if depth > 22 or split <= 0 or split >= len(pts) - 1:
        return [c]
    tc = norm(sub(pts[split - 1], pts[split + 1]))
    return (fit_cubic(pts[:split + 1], t1, tc, tol, depth + 1)
            + fit_cubic(pts[split:], (-tc[0], -tc[1]), t2, tol, depth + 1))


def fit_ring(ring, tol, corner_idx):
    n = len(ring)
    if not corner_idx:
        corner_idx = [0]
    out = []
    for k in range(len(corner_idx)):
        i, j = corner_idx[k], corner_idx[(k + 1) % len(corner_idx)]
        seg = ring[i:j + 1] if j > i else ring[i:] + ring[:j + 1]
        if len(seg) < 2:
            continue
        t1 = norm(sub(seg[1], seg[0]))
        t2 = norm(sub(seg[-2], seg[-1]))
        out += fit_cubic(seg, t1, t2, tol)
    return out


# ---------------------------------------------------------------- driver

def signed_area(ring):
    s = 0.0
    for i in range(len(ring)):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % len(ring)]
        s += x0 * y1 - x1 * y0
    return s / 2


def main():
    global SRC
    parser = argparse.ArgumentParser(description="Trace a two-colour concept image into cubic path data.")
    parser.add_argument("image", nargs="?", default=SRC, help="the concept image (default: art/concept.png)")
    args = parser.parse_args()
    SRC = args.image
    if not Path(SRC).is_file():
        sys.exit(f"trace-mark: {SRC} not found. Pass your concept image as an argument.")

    f, W, H = insideness()
    segs = marching_squares(f, W, H)
    rings = chain(segs)
    rings.sort(key=lambda r: abs(signed_area(r)), reverse=True)
    rings = [r for r in rings if abs(signed_area(r)) > 25][:2]
    print(f'contours: {[len(r) for r in rings]}  areas: {[round(signed_area(r)) for r in rings]}')

    curves = []
    for ri, ring in enumerate(rings):
        if ring[0] == ring[-1]:
            ring = ring[:-1]
        simp = rdp(ring + [ring[0]], DP_TOL)[:-1]
        cs = corners(simp, CORNER_DEG)
        fitted = fit_ring(simp, FIT_TOL, cs)
        print(f'  ring {ri}: {len(ring)} pts -> {len(simp)} simplified, '
              f'{len(cs)} corners -> {len(fitted)} cubics')
        curves.append((fitted, signed_area(ring)))
    # Normalise for mark.py: every subpath stored clockwise on screen (positive shoelace
    # with y downward, which is what `hole` reverses), centred on the silhouette's bounding
    # box, longest side UNITS. The eye is centred on the *outer* box, not its own, or it
    # would drift out of the head.
    paths = []
    for fitted, _ in curves:
        pts = [tuple(fitted[0][0])]
        for c in fitted:
            pts += [tuple(c[1]), tuple(c[2]), tuple(c[3])]
        if signed_area(pts) < 0:
            pts.reverse()
        paths.append(pts)

    xs = [p[0] for p in paths[0]]
    ys = [p[1] for p in paths[0]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    k = UNITS / max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    paths = [[(round((x - cx) * k, 2), round((y - cy) * k, 2)) for x, y in p] for p in paths]

    for name, pts in zip(('path_outer.txt', 'path_eye.txt'), paths):
        out = [f'M{pts[0][0]:g},{pts[0][1]:g}']
        for i in range(1, len(pts), 3):
            out.append('C' + ' '.join(f'{pts[i + j][0]:g},{pts[i + j][1]:g}' for j in range(3)))
        data = ''.join(out) + 'Z'
        open(name, 'w').write(data)
        print(f'\n--- {name}: {(len(pts) - 1) // 3} cubics, {len(data)} chars ---')
        print(data)


if __name__ == '__main__':
    main()
