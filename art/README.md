# Identity assets

Source art for the launcher icon and the Play listing. **Everything in `app/src/main/res` that draws
the mark is generated from here** — edit `mark.py` and regenerate, never hand-edit the path data in
the `VectorDrawable`s.

| Asset | Source | State |
| --- | --- | --- |
| `mark.py`'s MARK and EYE curves | your concept image → `trace-mark.py` | **placeholder — replace** |
| `drawable/ic_launcher_{foreground,monochrome}.xml`, `drawable/ic_notification.xml`, `mipmap-*`, `play-icon-512.png` | `mark.py` → `make-launcher-icon.py` | generated |
| `play-feature-graphic.png` (1024×500) | `mark.py` → `make-feature-graphic.py` | generated |
| `play-screenshots/<n>_<scene>-<tag>.png` | device capture → `pad-screenshot.py --crop-status-bar` | — |

## The mark

`mark.py` is the single definition, as **two cubic subpaths** — the silhouette and a hole punched
out of it. Both generators import it, so the launcher icon, the notification icon and the feature
graphic cannot drift into being different marks.

What ships today is a rounded triangle: deliberately generic, deliberately obviously a placeholder.

- **Recolouring is two values that nothing checks against each other**: `PRIMARY` in `mark.py`
  (which drives the mipmaps, the Play icon and the feature graphic's gradient) *and* the matching
  `fillColor` in `drawable/ic_launcher_background.xml`, which `make-launcher-icon.py` deliberately
  never writes. Changing one alone is the failure to expect.
- Take the colours from the app's generated scheme (`scripts/gen_scheme.py`) rather than picking
  them for the icon, so the identity and the app agree.
- **The hole must be a real hole in the path**, not a shape painted in the background colour. A
  themed launcher (API 33+) tints the whole monochrome layer one flat colour, and a painted hole
  simply vanishes.

## Where the art has to come from

**Use art you have the right to ship.** This is not a formality — it is the thing most likely to
block a first Play upload, and it is discovered late.

- An icon traced from an **emoji font** carries that font's licence. Noto Emoji is Apache-2.0 or
  OFL depending on the release, and both impose obligations on the *outlines* — which is what
  tracing copies.
- A **stock icon** is somebody's asset with somebody's terms, whatever the site's marketing says.
- **Art you drew, or art generated from your own prompt, is clean.** Keep a note of which, in this
  file, so the provenance survives you forgetting it.

Rendering *text* with a font is a different question from redistributing its *outlines*: the OFL
explicitly permits documents produced with a font. `make-feature-graphic.py` renders the wordmark
with Noto Sans on that basis and ships no glyph outlines.

## Replacing the mark

```bash
# 1. Draw or generate a concept image, and put it beside this file.
python3 art/trace-mark.py concept.png   # prints cubic path data
#    Paste MARK and EYE into art/mark.py, with your colours.

# 2. Regenerate everything that derives from it.
python3 art/make-launcher-icon.py       # icons, mipmaps, the 512² Play asset
python3 art/make-feature-graphic.py     # the 1024×500 listing graphic
```

`make-launcher-icon.py` prints a **safe-radius check** and will tell you when the art is clipped by
a circular launcher mask. It is a real constraint rather than a formality: a launcher may mask the
icon to a 66dp circle, so anything outside a 33dp radius from the centre is cut off. Shrink
`ART_SIZE` until it says `inside`.

Two sizes worth knowing, both already handled:

- The **notification icon** is scaled up relative to the launcher icon. At the launcher's own art
  size the mark would be a speck in a 24dp slot.
- The **flat mipmaps** are cropped to the 72dp a launcher actually shows of the 108dp adaptive
  canvas, so they match what the adaptive icon looks like rather than appearing to shrink.
