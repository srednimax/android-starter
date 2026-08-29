#!/usr/bin/env python3
"""Pad a device screenshot out to Play's 9:16 phone-screenshot ratio.

The test Xiaomi is 1220x2712, which is 2.22:1 — taller than the 9:16 Play documents for
phone screenshots. Rather than crop the UI or squash it, this centres the shot on a 9:16
canvas filled with the screenshot's own edge colour, so the padding reads as background
rather than as letterboxing.

    python3 art/pad-screenshot.py <in.png> <out.png>
    python3 art/pad-screenshot.py <in.png> <out.png> --crop-status-bar

`--crop-status-bar` removes the top [STATUS_BAR_PX] before padding. The driver holds the phone in
Do Not Disturb for the length of a run — see `set_dnd` in `scripts/edge-to-edge.py`, where the
alternative of revoking `POST_NOTIFICATIONS` is rejected because it makes the app draw a
blocked-state banner into the very screens that photograph reminder copy — and Zen puts a crossed
bell in the status bar of every frame. It cannot be suppressed on the device: HyperOS ignores
SystemUI demo mode outright (`sysui_demo_allowed` plus the clock/battery/notifications/zen
broadcasts change nothing), so the only place the bell can be removed is here. The clock and the
battery go with it, which is the point rather than a side effect — a listing shot of the app is
not a photograph of somebody's phone.
"""

import argparse
from collections import Counter

from PIL import Image

RATIO_W, RATIO_H = 9, 16

# The portrait `statusBars` inset on the test Xiaomi, measured by the edge-to-edge matrix rather
# than derived from a density: 130px at 480dpi, and it coincides with the punch-hole cutout, so one
# number takes both. See the table in `docs/edge-to-edge.md`. A different phone would need its own
# reading — this is a device constant, not a Play one.
STATUS_BAR_PX = 130


def edge_colour(img):
    """Most common pixel down the left and right edges — the app's background, not the
    status bar or the nav bar, both of which only touch the top and bottom."""
    px = img.load()
    w, h = img.size
    counts = Counter()
    for y in range(h // 8, h - h // 8):
        counts[px[0, y]] += 1
        counts[px[w - 1, y]] += 1
    return counts.most_common(1)[0][0]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("src")
    parser.add_argument("dst")
    parser.add_argument(
        "--crop-status-bar",
        action="store_true",
        help=f"drop the top {STATUS_BAR_PX}px (status bar and cutout) before padding",
    )
    args = parser.parse_args()

    src, dst = args.src, args.dst
    img = Image.open(src).convert("RGB")
    if args.crop_status_bar:
        img = img.crop((0, STATUS_BAR_PX, img.size[0], img.size[1]))
    w, h = img.size

    target_w = max(w, round(h * RATIO_W / RATIO_H))
    target_h = max(h, round(w * RATIO_H / RATIO_W))
    # Only one dimension actually grows; the other is already at or past the ratio.
    if target_w / target_h > RATIO_W / RATIO_H:
        target_h = round(target_w * RATIO_H / RATIO_W)
    else:
        target_w = round(target_h * RATIO_W / RATIO_H)

    canvas = Image.new("RGB", (target_w, target_h), edge_colour(img))
    canvas.paste(img, ((target_w - w) // 2, (target_h - h) // 2))
    canvas.save(dst, "PNG", optimize=True)

    ratio = target_w / target_h
    cropped = f" (status bar cropped, -{STATUS_BAR_PX}px)" if args.crop_status_bar else ""
    print(f"{dst}  {w}x{h} -> {target_w}x{target_h}  ({ratio:.4f}, 9:16 = {RATIO_W / RATIO_H:.4f}){cropped}")


if __name__ == "__main__":
    main()
