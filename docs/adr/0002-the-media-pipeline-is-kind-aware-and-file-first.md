# The media pipeline is kind-aware, writes the file before the row, and strips metadata

## Context

An app that stores images on the device has four problems that all look like one:

1. **Memory.** A 12 MP camera shot decoded at full size is ~48 MB of bitmap. A grid of them is an
   OOM crash on a mid-range phone.
2. **Orientation.** Cameras commonly leave pixels unrotated and record an EXIF orientation tag
   instead. Coil honours that tag on an untouched file — but re-encoding discards the tag and keeps
   the pixels sideways, so camera-taken images come out rotated while album-picked ones do not.
3. **Privacy.** A camera stamps GPS coordinates on every shot. An app that copies those into a
   backup is exporting the user's home address.
4. **Portability.** An absolute path changes across installs, so every restored backup points at
   files that are not there.

## Decision

**One function persists every image**: `MediaFiles.persist(uri, kind)`. Nothing else writes an image
file, ever.

**The kind selects both the directory and the downsample spec**, because the needs genuinely differ:
a thumbnail wants a small centre-cropped square, a photo a large long-edge cap, and a document
downsampled to photo dimensions makes small print unreadable. The directory doubles as the backup
export scope, so scopes are a list of `MediaKind` rather than a list of magic strings.

**Decode at roughly the size needed** (`inSampleSize`), apply the EXIF orientation to the *pixels*,
re-encode as JPEG. `Bitmap.compress` writes pixels only, so every EXIF tag — GPS included — is gone
by construction rather than by a removal step someone could forget.

**The capture date is read on the way past and returned**, because there is no going back: a column
added later could never be backfilled from files whose metadata has already been stripped.

**The file is written before the row**, and paths stored on the row are **relative**.

## Alternatives

**Store the original and downsample at draw time.** Costs the memory on every render instead of once,
and the backup carries full-resolution originals.

**Strip EXIF as a separate step.** A step that can be skipped will be skipped. Re-encoding makes it
structural.

**Row first, then file.** A crash in between leaves a dangling path, which to the user looks exactly
like the app losing their photo. File first leaves an invisible orphan, which costs disk and nothing
else — and "missing media renders as a placeholder" already covers the other direction.

## Consequences

- Quality numbers are measured, not guessed. The general rule behind them: **texture hides what text
  exposes** — a photograph tolerates quality 85 where a page of type does not, and that, not the
  pixel dimensions, is usually what decides the number.
- The crop is blind: there is no crop-and-zoom UI, so re-picking is the user's only recourse. Keep
  the crop centred and predictable.
- Nothing upscales. A 300 px source is stored at 300 px, not blown up with invented pixels.
