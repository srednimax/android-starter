#!/usr/bin/env python3
"""The notes gate: the release being cut must have Play release notes of its own.

Run by CI on every pull request, and worth running by hand before opening one:

    python3 scripts/notes-gate.py
    python3 scripts/notes-gate.py --report   # what does this branch owe?

The rule: **the version Play is told about is the version the notes describe.** `play-metadata.py`
takes the newest `### x.y.z` under `## Release notes` in docs/store-listing.md, and nothing else
consults it. So when release-please bumps `versionName` and the notes stay where they were, the
mismatch is silent and the *previous* release's text ships attached to the new build.

That is not hypothetical. 1.9.0 reached production on 2026-08-26 carrying 1.8.0's notes — text that
predates the timeline, multi-photo trays, kilogram entry and the light/dark override. Play does not
allow release notes to be edited on a live production release, so the correction could not be made
where it was needed; it had to wait for the next upload. A gate is cheaper than that.

Deliberately a gate rather than a test, for the same reason the translation gate is one: it has to
fail on release-please's PR, which is the one moment the two versions are allowed to disagree and the
last moment the disagreement can still be fixed for free.

Satisfying it when nothing owner-visible changed is one edit, not a rewrite. 1.8.0 is the precedent
already in the document: rename the heading and say why the nine bodies stand unchanged. The gate
reads the heading, so that decision stays deliberate instead of being made by default.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRADLE = ROOT / "app/build.gradle.kts"
LISTING = ROOT / "docs" / "store-listing.md"

# Anchored on release-please's own marker rather than on `versionName` alone: that comment is what
# the bump is applied to, so if it ever moves this gate should fail loudly rather than read some
# other line that happens to look similar.
VERSION_NAME = re.compile(r'versionName\s*=\s*"(?P<version>\d+\.\d+\.\d+)"\s*//\s*x-release-please-version')
VERSION_HEADING = re.compile(r"^###\s+(?P<version>\d+\.\d+\.\d+)")


def whatsnew():
    """Import play-whatsnew.py, whose filename is not a valid module name.

    Reused rather than reimplemented: it already knows how to find the Release notes section, which
    locales the AAB actually ships, and Play's 500-character limit. A second copy of that would be a
    second thing to keep true.
    """
    path = Path(__file__).parent / "play-whatsnew.py"
    spec = importlib.util.spec_from_file_location("play_whatsnew", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["play_whatsnew"] = module
    spec.loader.exec_module(module)
    return module


def version_name() -> str:
    match = VERSION_NAME.search(GRADLE.read_text(encoding="utf-8"))
    if not match:
        sys.exit(
            f"no `versionName = \"x.y.z\" // x-release-please-version` in {GRADLE.relative_to(ROOT)}.\n"
            "release-please writes that line; without it neither the bump nor this gate works."
        )
    return match.group("version")


def notes_versions(text: str) -> list[str]:
    """Every `### x.y.z` under `## Release notes`, in document order (newest last)."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("## Release notes")), None)
    if start is None:
        sys.exit(f"no '## Release notes' section in {LISTING.relative_to(ROOT)}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return [m.group("version") for line in lines[start:end] if (m := VERSION_HEADING.match(line))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--report", action="store_true", help="print the state and always exit 0")
    args = parser.parse_args()

    shipping = version_name()
    text = LISTING.read_text(encoding="utf-8")
    versions = notes_versions(text)
    if not versions:
        sys.exit(f"no '### <version>' subsection under Release notes in {LISTING.relative_to(ROOT)}")
    newest = versions[-1]

    if newest != shipping:
        message = (
            f"versionName is {shipping}, but the newest release notes are for {newest}.\n\n"
            f"play-metadata.py uploads the newest notes it finds, so {shipping} would ship {newest}'s\n"
            f"text — which is exactly how 1.9.0 reached production describing 1.8.0. Play will not let\n"
            f"you edit notes on a live release, so this is the last cheap moment to fix it.\n\n"
            f"Add `### {shipping}` to the Release notes section of {LISTING.relative_to(ROOT)}, after\n"
            f"`### {newest}`, with a fenced note per shipped locale.\n\n"
            f"If nothing owner-visible changed, that is a rename, not a rewrite: move the heading to\n"
            f"{shipping} and say why the bodies stand unchanged. 1.8.0 is the worked example."
        )
        if args.report:
            print(f"OWED: {message}")
            return 0
        sys.exit(message)

    # The version matches; now prove the note set behind it is actually usable. play-whatsnew
    # already enforces both halves, so failing here means the notes exist but could not ship.
    module = whatsnew()
    _, notes = module.parse(text, shipping)
    shipped = module.shipped_locales()
    missing = sorted(shipped - notes.keys())
    if missing:
        sys.exit(
            f"{shipping} has notes for {len(notes)} locales but the app ships {len(shipped)}.\n"
            f"Missing: {', '.join(missing)}.\n"
            "A language the build carries and the listing does not falls back to English in the store."
        )
    over = {locale: len(body) for locale, body in notes.items() if len(body) > module.LIMIT}
    if over:
        detail = ", ".join(f"{locale} {n}/{module.LIMIT}" for locale, n in sorted(over.items()))
        sys.exit(f"{shipping} has notes over Play's limit: {detail}.\nPlay truncates rather than warns.")

    longest = max(len(body) for body in notes.values())
    print(f"notes gate: {shipping} has {len(notes)} locales, longest {longest}/{module.LIMIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
