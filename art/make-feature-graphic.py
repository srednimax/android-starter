#!/usr/bin/env python3
"""Render the 1024x500 Play feature graphic to art/play-feature-graphic.png.

Original art only: the mark comes from `mark.py`, the same declaration the launcher
icon is generated from, so the two assets cannot drift into being different marks. Text
is *rendered* with Noto Sans, which the OFL explicitly permits without any notice — what
it restricts is redistributing glyph outlines as art.

    python3 art/make-feature-graphic.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import mark

# The three strings this graphic is *about*. Edit them; everything else is layout.
APP_NAME = "Starter"
TAGLINE = "Replace this with one line about your app"
FEATURES = "Private  ·  Offline  ·  No ads  ·  Free"

OUT = Path(__file__).parent / "play-feature-graphic.png"
W, H = 1024, 500
S = 4  # supersample factor; everything below is in final pixels, scaled by S at draw time

# Shared with the launcher icon, so the two read as one identity.
PRIMARY, PRIMARY_DARK, SURFACE = mark.PRIMARY, mark.PRIMARY_DARK, mark.SURFACE
# Two steps down from SURFACE towards the ground, so the three text weights read as one family
# against the ground. Tinted rather than grey: a neutral grey on a coloured ground looks like a mistake.
TAGLINE_INK = (0xC6, 0xD4, 0xE8)
SUBTLE = (0x99, 0xAB, 0xC6)

FONT_DIR = Path("/usr/share/fonts/truetype/noto")
FONT_BOLD = FONT_DIR / "NotoSans-Bold.ttf"
FONT_REG = FONT_DIR / "NotoSans-Regular.ttf"


def gradient(size, top_left, bottom_right):
    """Diagonal two-stop gradient. Built at 1px per step along the diagonal, then resized."""
    w, h = size
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            # normalised distance along the top-left -> bottom-right diagonal
            t = (x / w + y / h) / 2
            px[x, y] = tuple(round(a + (b - a) * t) for a, b in zip(top_left, bottom_right))
    return img


def draw_mark(base, ox, oy):
    """The shared mark from `mark.py`, drawn at (ox, oy) in final pixels.

    Painted onto its own layer so the eye can be punched to full transparency rather than
    filled with a guess at the ground colour — the background here is a gradient, so a
    painted eye would only match at one height. The launcher icon gets the same hole from
    the same declaration, by winding rather than by alpha.
    """
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    def tf(p):
        return ((ox + p[0]) * S, (oy + p[1]) * S)

    for e in mark.PARTS:
        d.polygon(mark.outline(e, tf), fill=(0, 0, 0, 0) if e.hole else SURFACE + (255,))
    base.alpha_composite(layer)


def draw_trend(base, points, colour, width):
    """The weight chart's own motif: irregular x spacing, because that is the honest shape
    of real weighings and the one thing the app refuses to fake (see CLAUDE.md)."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    scaled = [(x * S, y * S) for x, y in points]
    ld.line(scaled, fill=colour, width=width * S, joint="curve")
    for x, y in scaled:
        r = width * S * 1.9
        ld.ellipse([x - r, y - r, x + r, y + r], fill=colour)
    base.alpha_composite(layer)


def main():
    base = gradient((W, H), PRIMARY, PRIMARY_DARK).convert("RGBA")
    base = base.resize((W * S, H * S), Image.BICUBIC)

    # Background trend line, low contrast so it reads as texture rather than a chart.
    draw_trend(
        base,
        [(72, 432), (152, 417), (198, 423), (300, 400), (356, 406), (470, 384),
         (598, 374), (666, 381), (788, 358), (886, 351), (958, 342)],
        (0xFF, 0xFF, 0xFF, 26),
        3,
    )

    draw_mark(base, ox=852, oy=252)

    d = ImageDraw.Draw(base)
    wordmark = ImageFont.truetype(str(FONT_BOLD), 116 * S)
    tagline = ImageFont.truetype(str(FONT_REG), 38 * S)
    features = ImageFont.truetype(str(FONT_REG), 27 * S)

    x = 74 * S
    d.text((x, 150 * S), APP_NAME, font=wordmark, fill=SURFACE, anchor="ls")
    d.text((x, 212 * S), TAGLINE, font=tagline, fill=TAGLINE_INK, anchor="ls")
    d.text((x, 300 * S), FEATURES, font=features, fill=SUBTLE, anchor="ls")

    out = base.resize((W, H), Image.LANCZOS).convert("RGB")  # RGB: Play rejects alpha
    out.save(OUT, "PNG", optimize=True)
    print(f"{OUT}  {out.size[0]}x{out.size[1]}  {OUT.stat().st_size / 1024:.0f} KiB  mode={out.mode}")


if __name__ == "__main__":
    main()
