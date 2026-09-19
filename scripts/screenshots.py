#!/usr/bin/env python3
"""Capture every screen in light and dark — the before/after record of a redesign, and the listing's set.

A redesign changes how the app looks and says nothing about what it does, which makes "is this
better?" the only question that matters and the hardest one to answer honestly. The answer is a
*before* set: every screen, shot before a line changes, so the comparison at the end is against a
record rather than against a memory of what the old one looked like.

This is not `edge-to-edge.py` with different flags — it is the same walk with a different axis and a
different output. That script's matrix is **rotation x navigation mode** and its deliverable is the
inset arithmetic; this one's matrix is **theme x locale** and its deliverable is the PNG. So the tap
sequences are imported from it rather than copied: [SCENES] is the expensive asset in this repo and
two drifting copies of it would both keep producing screenshots, just of the wrong screens.

⚠ **[SCENES] describes the template's placeholder screens.** Rewrite it against your own the day the
placeholder domain goes — until then a run walks to screens that do not exist, and the nightly
edge-to-edge job reports a red that means nothing. That rewrite is the one edit that makes both
scripts yours; everything else here is about the phone, not the app.

    scripts/screenshots.py --out docs/screenshots/before
    scripts/screenshots.py --out docs/screenshots/after
    scripts/screenshots.py --out DIR --theme light          # one cell
    scripts/screenshots.py --out DIR --scene items,settings # one screen, while iterating
    scripts/screenshots.py --out DIR --scene items,settings --numbered   # 1_items-en.png, 2_settings-en.png
    scripts/screenshots.py --out DIR --build release --numbered --scene …  # the store set, see below
    scripts/screenshots.py --restore                        # hand the phone back

**A store set comes from the shipped build** — `--build release`, which drives the release
applicationId instead of `.debug`. The developer-only Settings section lives in `app/src/debug/`, so
only the shipped build is free of it. That install is somebody's real app, so the flag also implies
`--no-reseed` and the wipe refuses outright: the shots show whatever is really set up on it.

Filenames carry the locale they were taken in — `items-pl.png`, not `items.png` — because a PNG loses
the directory that used to carry its language the moment anyone moves it. See [locale_tag].

`--numbered` additionally prefixes each file with its position in the `--scene` list — `1_items-pl.png`.
Play orders a listing's screenshots by the order they are uploaded, and a file manager sorts
alphabetically, so without the prefix the set sorts by scene name rather than by intent. The number
comes from the order **asked for**, not from [SCENES], which is why `--scene` preserves its argument
order rather than the table's. Opt-in, because every other consumer of these filenames — the
before/after comparisons, the manifest — refers to them without one.

Each cell runs the suites in the one order that works: `full` against the seeded sample data, then
`mismatch` (only when the app has a database), then `empty` — which wipes the install and is
therefore last. Each cell then reseeds, so the next one starts from the same place and the phone is
left usable rather than blank.

**The phone's own state is borrowed and handed back**: rotation, navigation mode, per-app locale on
both installs, Do Not Disturb, the status bar (SystemUI demo mode, so a listing does not ship your
notification icons and battery level), and the dark-theme setting — read before the first cell and
restored afterwards, never guessed.

**It wipes the debug install** (`<applicationId>.debug`, from `project.py`), and with it anything
armed there. Every cell reseeds, and reseeding is correct from the script's side, so nothing warns: the
app this template was extracted from lost an alarm it had been waiting two weeks to read that way. **Check the
debug install for armed state before running this**, or accept that it is gone.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

# `edge-to-edge.py` is not an importable module name — the hyphen makes it un-`import`-able by the
# ordinary statement, so it is loaded by path instead. Renaming it was the alternative and it is
# referenced by name in CI and the docs; a loader stanza is the cheaper edge.
_SPEC = importlib.util.spec_from_file_location("edge_to_edge", Path(__file__).parent / "edge-to-edge.py")
e2e = importlib.util.module_from_spec(_SPEC)
# Registered before it executes, not after: `@dataclass` resolves `cls.__module__` through
# `sys.modules` while the class body runs (Python 3.12+), and `Config` is decorated at import time.
# Without this line the import dies on a `NoneType has no attribute '__dict__'` from dataclasses.
sys.modules["edge_to_edge"] = e2e
_SPEC.loader.exec_module(e2e)


# --------------------------------------------------------------------------------------------
# The cells
# --------------------------------------------------------------------------------------------

# Portrait + gesture only, and that is a deliberate narrowing rather than an oversight. Orientation
# and navigation mode are what `edge-to-edge.py` exists to cover; repeating those four cells here
# would shoot the same design four times to learn nothing about the design.
CONFIG = e2e.Config("portrait-gesture", 0, "gesture")

# Dark is not a variant of light and does not review as one. Contrast, elevation and the surface
# roles all land differently, and a palette settled in light alone is a palette re-settled in dark
# later — which is the redesign done twice.
THEMES = {"light": "no", "dark": "yes"}

# The order is the whole point. `empty` wipes, so it goes last or it takes the sample data the `full`
# suite needs out from under it. `mismatch` corrupts the schema version and puts it back, which is
# survivable in the middle; it is second because it is cheap and because running it after a wipe
# would corrupt a database with nothing in it.
# `mismatch` fakes a schema the build cannot open, which needs a database to fake it in — an app
# that has deleted Room has neither the file nor the refusal screen (scripts/project.py).
SUITES = ("full", "mismatch", "empty") if e2e.project.HAS_DATABASE else ("full", "empty")


def app_theme_default() -> "str | None":
    """The theme a freshly cleared install starts on, read from `AppPreferences.kt`'s fallback.

    **This is what decides whether [set_theme] is a lever at all.** Every cell begins with a
    `pm clear`, so the app is on its *default* before the first tap. While that default is
    `ThemeMode.SYSTEM` the app follows `cmd uimode night` and both cells work. The day the default
    becomes `DARK` (or `LIGHT`), the system setting moves nothing — and nothing fails: an app built
    from this template walked a whole light cell, wrote six files under `light/` and reported
    success, and every one of them was dark. So [main] asks this first and refuses the cell the
    lever can no longer reach. None when the fallback cannot be read, which only warns.
    """
    source = e2e.project.MAIN_SRC / "data/AppPreferences.kt"
    if not source.is_file():
        return None
    found = re.search(r"\?:\s*ThemeMode\.(\w+)", source.read_text(encoding="utf-8"))
    return found.group(1) if found else None


def set_theme(theme: str) -> None:
    """Flip the system dark theme. The app follows it while its stored theme is SYSTEM — the default.

    The in-app preference (Settings → Appearance) is the other lever, and a cleared install starts
    on its default, which is why the device setting works here. See [app_theme_default] for when it
    stops working and how [main] notices.
    """
    e2e.shell(f"cmd uimode night {THEMES[theme]}")
    # The mode change restarts activities out of process. Nothing publishes a "the new configuration
    # has landed" signal that arrives before the recomposition does, so this is a wait; every scene
    # force-stops and relaunches anyway, which is the real guarantee.
    e2e.settle(2.5)


def read_theme() -> tuple[str, bool]:
    """The phone's own dark-theme mode before the run moves it, and whether a one-off toggle rode on it.

    **Read, never assumed.** `--restore` used to write back `auto`, which is not "whatever the phone
    had" but Android's sunset-to-sunrise schedule: a phone set to dark was still dark at bedtime and
    light again by morning. `cmd uimode night` prints its mode as the same word it accepts — `yes`,
    `no`, `auto`, `custom`, and `custom_schedule` / `custom_bedtime` from API 34 — so the reading is
    also the command that puts it back.

    **The override is the half that cannot go back, and it is a platform limit.** Toggling dark from
    Quick Settings while the mode is `auto` or `custom` does not change the mode; it sets an override
    that lasts until the schedule's next transition. The run's first `yes`/`no` clears it and no
    shell verb sets one, so the most this script can do is say so.
    """
    mode = e2e.shell("cmd uimode night").split(":", 1)[-1].strip()
    flags = re.search(r"mOverrideOn/Off=(\w+)/(\w+)", e2e.shell("dumpsys uimode"))
    overridden = mode not in ("yes", "no") and flags is not None and "true" in flags.groups()
    return mode, overridden


def restore_theme(mode: str, overridden: bool) -> None:
    """Put back what [read_theme] saw. Leaves the phone alone rather than guess at an unreadable mode."""
    if mode in ("", "unknown"):
        print("  -- note: the phone's dark theme read as unknown before the run; left as the run left it")
        return
    e2e.shell(f"cmd uimode night {mode}")
    if overridden:
        print(
            f"  -- note: dark theme is back on `{mode}`, but the one-off Quick Settings toggle on top of"
            " it is gone — the phone follows its schedule until that toggle is tapped again"
        )


# The locale lever moved to `edge-to-edge.py`, beside the needle table it has to agree with — the
# same argument that imports [SCENES] rather than copying them. `wipe` there re-applies it after
# every `pm clear`, so this script no longer re-pins it per suite: the `empty` suite wipes as its
# first *step*, which a once-per-suite call could never have covered anyway.
set_locale = e2e.set_locale


def locale_tag(locale: str | None) -> str:
    """The BCP-47 tag a screenshot was actually taken in, for its filename.

    The tag goes in the **filename** rather than only in the manifest because a PNG gets moved,
    renamed, pasted into the Console and mailed to a translator, and every one of those strips the
    directory it came from. Nine locales of one scene are otherwise nine files called `home.png`
    that differ only by which folder they sit in — which is exactly the state a mis-upload is made
    of, and no amount of care at upload time can recover the language from the pixels.

    When `--locale` is omitted the app runs in the *phone's* language, so the tag is read back off
    the device rather than left blank. `getprop` returns a POSIX-flavoured `pl_PL`; the separator is
    normalised to BCP-47's hyphen so a device-default run and an explicit `--locale pl-PL` produce
    the same name for the same thing.
    """
    if locale is not None:
        return locale
    for prop in ("persist.sys.locale", "ro.product.locale"):
        value = e2e.shell(f"getprop {prop}").strip()
        if value:
            return value.replace("_", "-")
    # Never seen on a real device; a name that says so beats a name that quietly omits the tag,
    # because the whole point of the suffix is that it is always there to read.
    return "unknown"


# --------------------------------------------------------------------------------------------
# Capture
# --------------------------------------------------------------------------------------------


# Scene name -> its 1-based position in the `--scene` list, empty unless `--numbered` was asked for.
# A module global rather than a parameter threaded through `run_cell`, matching how the driver already
# carries per-run device state.
_ORDER: dict[str, int] = {}


def capture(scene, out_dir: Path, tag: str) -> dict:
    """Walk to one scene and shoot it. No inset checking — that is `edge-to-edge.py`'s job.

    [tag] is the locale suffix the file is named with — see [locale_tag] for why it is in the name
    and not only in the manifest.
    """
    error = e2e.reach_scene(scene)
    if error is not None:
        return {"scene": scene.name, "family": scene.family, "error": error}

    e2e.settle(0.8)
    # Padded only when the set actually reaches double digits. A Play listing is capped at 8, where
    # `1_` is what you want and `01_` is noise; but the capture suite is 30-odd scenes and nothing
    # stops someone numbering all of them, and there `10_` unpadded would sort between 1 and 2.
    width = 2 if len(_ORDER) >= 10 else 1
    prefix = f"{_ORDER[scene.name]:0{width}d}_" if scene.name in _ORDER else ""
    shot = out_dir / f"{prefix}{scene.name}-{tag}.png"
    shot.write_bytes(e2e.adb("exec-out", "screencap", "-p", binary=True))
    return {
        "scene": scene.name,
        "family": scene.family,
        "note": scene.note,
        "screenshot": str(shot.relative_to(out_dir.parent)),
        "bytes": shot.stat().st_size,
    }


def run_cell(theme: str, locale: str | None, scenes: list, out: Path, reseed: bool) -> dict:
    """One theme, every suite, in [SUITES] order.

    The reseed is at the *start* rather than the end, and that is the load-bearing detail of the
    whole script. Anything the seed stages for one scene — a one-shot prompt, see
    `Scene.keeps_seeded_prompt` — is consumed by the first cell, so a second cell inheriting the
    first one's install finds it already gone and shoots an ordinary screen under the prompt's name.
    Starting each cell from a fresh seed is what makes light and dark comparable at all, rather than
    a pair that quietly diverges after scene one.
    """
    out_dir = out / theme
    out_dir.mkdir(parents=True, exist_ok=True)
    # Resolved once per cell rather than per scene: it is a `getprop` round trip when the run
    # has no --locale, and the phone's language cannot change underneath a single cell.
    tag = locale_tag(locale)

    if reseed:
        # Invalidated first, so a cell always reseeds even when the previous one left the same seed
        # on the phone — a consumed one-shot prompt is the reason (see above), and only a fresh
        # seed brings it back. `min` picks the seed the *first* scene will want: scenes are sorted by
        # seed, "" sorts first, so this is "" unless every scene here is a variant one.
        e2e.invalidate_seed()
        e2e.ensure_seed(min((scene.seed for scene in scenes if scene.suite == "full"), default=""))
    set_theme(theme)

    results = []
    # Set while the database on disk claims a schema this build cannot open, and cleared the moment
    # it is put back. Not "did the mismatch suite run?" — that question has the wrong answer by the
    # end of a cell, because `empty` runs afterwards and its `pm clear` deletes the backup file the
    # restore reads. Restoring then fails on a missing file and takes the whole run down with it,
    # which is what killed the dark cell on the first attempt.
    schema_dirty = False
    try:
        for suite in SUITES:
            wanted = [scene for scene in scenes if scene.suite == suite]
            if not wanted:
                continue
            # Seed group first, then any scene that photographs a seeded one-shot prompt — before
            # every other scene dismisses it for good. The same order and the same reasons as
            # `edge-to-edge.py`'s [run_matrix]; sorting is stable, so everything else keeps its
            # declared order.
            wanted.sort(key=lambda scene: (scene.seed, not scene.keeps_seeded_prompt))
            schema_dirty = schema_dirty or suite == "mismatch"
            print(f"  -- {suite} ({len(wanted)} scenes)")
            for scene in wanted:
                if suite == "full" and reseed:
                    e2e.ensure_seed(scene.seed)
                elif scene.seed:
                    # **Skipped rather than shot.** `--no-reseed` is the iterate-on-one-screen flag,
                    # and a scene whose whole point is a state the default fixture hides would come
                    # back as an ordinary screenshot under a name claiming otherwise. A cell that
                    # cannot fail is not evidence; a scene that says it did not run is.
                    results.append(
                        {"scene": scene.name, "family": scene.family, "error": f"needs seed {scene.seed!r}; --no-reseed"},
                    )
                    print(f"     {scene.name:28s} SKIPPED  needs seed {scene.seed!r}")
                    continue
                result = capture(scene, out_dir, tag)
                results.append(result)
                if "error" in result:
                    print(f"     {scene.name:28s} SKIPPED  {result['error'][:80]}")
                else:
                    print(f"     {scene.name:28s} {result['bytes'] // 1024:>5d} KB")
            if schema_dirty:
                # Immediately, while the backup still exists — not deferred to the `finally`.
                e2e.restore_schema_version()
                schema_dirty = False
    finally:
        # Only reachable when a scene threw mid-mismatch, which is exactly when a phone left claiming
        # a schema this build cannot open is hardest to explain.
        if schema_dirty:
            e2e.restore_schema_version()

    return {"theme": theme, "locale": locale or "device default", "scenes": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, help="directory for the screenshots and the manifest")
    parser.add_argument("--theme", help="comma-separated: light,dark. Default both")
    parser.add_argument("--scene", help="comma-separated scene names. Default every scene, all suites")
    parser.add_argument(
        "--locale",
        help="BCP-47 tag pinned as the app's language, e.g. pl. Default leaves the device default alone",
    )
    parser.add_argument("--restore", action="store_true", help="undo the pinned rotation, nav mode and locale")
    parser.add_argument(
        "--numbered",
        action="store_true",
        help=(
            "prefix each file with its position in --scene, e.g. 1_home-pl.png, so a listing's "
            "screenshots sort into the order they should be uploaded in"
        ),
    )
    parser.add_argument(
        "--build",
        choices=["debug", "release"],
        default="debug",
        help="which install to shoot. 'release' is the shipped one — the only one a store set should "
        "come from — and implies --no-reseed",
    )
    parser.add_argument(
        "--no-reseed",
        action="store_true",
        help="skip the wipe-and-seed each cell starts with. For iterating on one screen, not for a full set",
    )
    args = parser.parse_args()

    if args.restore:
        e2e.restore_device()
        # **Both installs, not the one `--build` happens to name** — see edge-to-edge.py's --restore.
        for build in ("debug", "release"):
            e2e.select_build(build)
            set_locale(None)
        # No theme here: a separate invocation has no record of what the phone had, and writing a
        # guess is how this line used to leave a dark phone on Android's sunset schedule (`auto` is
        # not "whatever it was"). A run puts the theme back itself — see [read_theme].
        print("rotation, navigation mode, locale, Do Not Disturb and the status bar handed back to the phone")
        return 0

    e2e.select_build(args.build)
    if args.build == "release" and not args.no_reseed:
        # Not an error: the shipped install is already "seeded" in the only sense that matters — it
        # is an app in use — and the wipe would refuse anyway. Said out loud because it changes what
        # the shots show: real settings, and whatever theme is actually set.
        print("-- --build release implies --no-reseed: the shipped install is never wiped")
        args.no_reseed = True

    if not args.out:
        parser.error("--out is required unless --restore")

    themes = list(THEMES)
    if args.theme:
        wanted = set(args.theme.split(","))
        unknown = wanted - set(THEMES)
        if unknown:
            parser.error(f"unknown theme(s): {', '.join(sorted(unknown))}")
        themes = [theme for theme in THEMES if theme in wanted]

    # **Refused rather than shot wrong.** See [app_theme_default]: once a cleared install no longer
    # starts on SYSTEM, `cmd uimode night` cannot reach the app, and the cell it cannot reach would
    # write the other theme's pixels under this theme's name and report success. It refuses the
    # *default* too, which is the point: leaving `--out DIR` as a silent half-truth keeps the trap
    # open for exactly the person who has not read this file.
    default = app_theme_default()
    if default is None:
        print("-- note: could not read ThemeMode's fallback in AppPreferences.kt; trusting cmd uimode")
    elif default in ("DARK", "LIGHT"):
        stuck = [theme for theme in themes if theme != default.lower()]
        if stuck:
            parser.error(
                f"the {', '.join(stuck)} cell cannot be captured: AppPreferences' theme defaults to "
                f"{default}, so a cleared install ignores `cmd uimode night`. Use --theme {default.lower()}, "
                "or drive Settings -> Appearance after each reseed",
            )

    scenes = list(e2e.SCENES)
    if args.scene:
        # A list, not a set: under --numbered the order asked for *is* the listing's order, and a set
        # would silently substitute SCENES' own ordering for the one that was typed.
        wanted = [name.strip() for name in args.scene.split(",") if name.strip()]
        unknown = set(wanted) - {scene.name for scene in scenes}
        if unknown:
            parser.error(f"unknown scene(s): {', '.join(sorted(unknown))}")
        by_name = {scene.name: scene for scene in scenes}
        scenes = [by_name[name] for name in wanted]
    elif args.numbered:
        parser.error("--numbered needs --scene: the number is the position in the list you asked for")

    if args.numbered:
        global _ORDER
        _ORDER = {scene.name: i for i, scene in enumerate(scenes, 1)}

    # Needles first, phone second: an ambiguous or missing one is a fact about this repository, and
    # finding it out before the first tap is the difference between a minute and an evening.
    if args.locale:
        e2e.resolve_needles(args.locale)
    set_locale(args.locale)

    e2e.apply_config(CONFIG)
    started = time.time()
    manifest = {
        "config": CONFIG.name,
        "themes": [],
        # the app's own generated scheme: `dynamicColor` defaults **off**
        # (ADR-0006) and every cell here starts from a wipe, so the Material You toggle is at its
        # default and the colours are reproducible from `theme/Color.kt` alone.
        #
        # The *before* set is not, and the difference is the point rather than a caveat: it was shot
        # while `dynamicColor = true`, so its colours are this phone's wallpaper on that day. Compare
        # the two sets on structure, density and copy — which is what the set is read for — and never
        # on hue, where the before half is not a fixed target.
        "dynamic_color": "off — the app's own scheme (ADR-0006)",
    }
    # Do Not Disturb for the length of the run, off again whatever happens — a seeded reminder can
    # post a heads-up banner over the screen a minute after every reseed, and this script reseeds
    # once per cell. See [e2e.set_dnd]; the `finally` is because it is a phone-wide setting.
    # The theme is phone-wide too, so it is read before the first cell writes it and put back in the
    # same `finally`. So is the status bar, which demo mode empties of this phone's own icons — see
    # [e2e.set_demo_status_bar]; a status bar left in demo mode looks like a broken phone.
    phone_theme = read_theme()
    e2e.set_dnd(True)
    e2e.set_demo_status_bar(True)
    try:
        for theme in themes:
            print(f"\n=== {theme}")
            manifest["themes"].append(run_cell(theme, args.locale, scenes, args.out, not args.no_reseed))

        # The `empty` suite ends with the install wiped, so without this the phone is handed back
        # blank. Only owed when a wipe happened.
        if any(scene.suite == "empty" for scene in scenes) and not args.no_reseed:
            print("\n-- reseeding, so the phone is left usable")
            e2e.reset_to_seeded()
    finally:
        e2e.set_dnd(False)
        e2e.set_demo_status_bar(False)
        restore_theme(*phone_theme)

    manifest["seconds"] = round(time.time() - started)
    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    shot_count = sum(1 for cell in manifest["themes"] for scene in cell["scenes"] if "error" not in scene)
    failed = [scene["scene"] for cell in manifest["themes"] for scene in cell["scenes"] if "error" in scene]
    print(f"\n{shot_count} screenshots in {manifest['seconds']}s -> {args.out}")
    if failed:
        print(f"{len(failed)} scene(s) never reached: {', '.join(sorted(set(failed)))}")
    print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
