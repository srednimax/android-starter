#!/usr/bin/env python3
"""Turn this template into a named app. Run once, then delete this file.

    python3 bootstrap.py --name "Kettle" --namespace app.kettle --appid com.example.kettle

What it changes, and nothing else:

  * `app/build.gradle.kts`   — namespace, applicationId, versionName back to 0.1.0
  * `app/src/*/java/…`       — the package directories are moved, and every `package`/`import`
                               line in every `.kt` file is rewritten
  * `scripts/project.py`     — APP_NAME and DATABASE_FILE
  * `scripts/gen_scheme.py`  — the package the generated Color.kt declares
  * `res/values*/strings.xml`— `app_name`
  * `release-please-config.json`, `.release-please-manifest.json`, `CHANGELOG.md`
  * `docs/_config.yml`       — the Pages site title
  * `fastlane/Appfile`, the two publish workflows — the Play package name
  * `app/schemas/`           — the exported schema moves with the database class
  * `.claude/settings.json`  — the Claude Code push hook (created; the template has none, see PUSH_HOOK)

**It does not touch the Kotlin class names**, and that is deliberate. Everything is called
`AppDatabase`, `AppTheme`, `AppPreferences`, `MainApplication` — names that stay correct whatever the
app is called, so a rename is a package move rather than a repo-wide find-and-replace with all the
false positives that implies. Rename them later if you want to; nothing depends on their spelling
except `scripts/project.py`, which says so.

## Choosing the two names

**`--appid` is the one that can never change.** A Play Console package name is fixed the moment the
app entry is created: not renameable, not transferable to a new listing without losing every install
and review. Choose it as if you were choosing a domain. `--namespace` is only the Kotlin package
root and can be refactored any afternoon, so it is fine for the two to disagree — and they often
should, because a good store identity and a good source package have different constraints.

## Afterwards

    ./gradlew assembleDebug test
    python3 scripts/gen_scheme.py > app/src/main/java/<namespace as dirs>/theme/Color.kt
    $EDITOR art/mark.py            # replace the placeholder mark
    rm bootstrap.py
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TEMPLATE_NAMESPACE = "app.starter"
TEMPLATE_APP_ID = "com.example.starter"
TEMPLATE_NAME = "Starter"

# The Claude Code hook that runs `notes-gate.py --pending` before every `git push` Claude makes, so a
# release's Play notes are written on the branch that brings the change instead of in a docs PR after
# release-please's PR fails the notes gate. Installed here, not committed to the template, because the
# template never releases: its own `feat:` commits would make every push to it owe notes for a version
# that will never ship. An app does release, so it gets the hook the moment it becomes one.
PUSH_HOOK = {
    "matcher": "Bash",
    "hooks": [
        {
            "type": "command",
            "if": "Bash(git push*)",
            "command": 'git -C "$CLAUDE_PROJECT_DIR" fetch -q origin main 2>/dev/null; '
            'python3 "$CLAUDE_PROJECT_DIR/scripts/notes-gate.py" --pending',
            "timeout": 30,
            "statusMessage": "Checking the next release has its notes",
        }
    ],
}

# Where Kotlin lives, per source set. `debug` and `release` are the developer-surface seam.
SOURCE_SETS = ["main", "test", "androidTest", "debug", "release"]

VALID_PACKAGE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


def fail(message: str) -> None:
    print(f"bootstrap: {message}", file=sys.stderr)
    raise SystemExit(2)


def check(namespace: str, app_id: str) -> None:
    for label, value in [("--namespace", namespace), ("--appid", app_id)]:
        if not VALID_PACKAGE.match(value):
            fail(
                f"{label} '{value}' is not a valid package name: lowercase segments separated by "
                "dots, at least two of them, starting with a letter."
            )
        # `class` and friends are legal directory names and illegal Kotlin package segments, and the
        # error you get otherwise is a compile failure a long way from here.
        reserved = {"in", "is", "as", "for", "fun", "if", "else", "when", "object", "class", "val", "var", "try", "do"}
        bad = reserved.intersection(value.split("."))
        if bad:
            fail(f"{label} '{value}' contains the Kotlin keyword(s) {', '.join(sorted(bad))}")


def move_sources(namespace: str) -> None:
    """Move each source set's package directory, then rewrite the package lines inside."""
    old_rel = Path(TEMPLATE_NAMESPACE.replace(".", "/"))
    new_rel = Path(namespace.replace(".", "/"))
    if old_rel == new_rel:
        return

    for source_set in SOURCE_SETS:
        base = ROOT / "app/src" / source_set / "java"
        old = base / old_rel
        if not old.is_dir():
            continue
        new = base / new_rel
        new.parent.mkdir(parents=True, exist_ok=True)
        if new.exists():
            fail(f"{new} already exists — refusing to merge two package trees")
        shutil.move(str(old), str(new))

        # Remove the now-empty parents of the old location, but never the source set's own `java`.
        parent = old.parent
        while parent != base and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent


def rewrite(path: Path, replacements: list[tuple[str, str]]) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    original = text
    for old, new in replacements:
        text = text.replace(old, new)
    if text == original:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rename this template into a new app.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--name", required=True, help='Human name, e.g. "Kettle". Shown on the launcher.')
    parser.add_argument("--namespace", required=True, help="Kotlin package root, e.g. app.kettle")
    parser.add_argument("--appid", required=True, help="Play package name — permanent. e.g. com.example.kettle")
    parser.add_argument("--db", help="Database filename (default: <lowercased name>.db)")
    parser.add_argument(
        "--keep-git",
        action="store_true",
        help="Keep this repository's git history. The default is to leave git alone entirely; "
        "pass --fresh-git to start a new history instead.",
    )
    parser.add_argument(
        "--fresh-git",
        action="store_true",
        help="Delete .git and start a new repository with one initial commit.",
    )
    parser.add_argument("-n", "--dry-run", action="store_true", help="Print what would change and stop.")
    args = parser.parse_args()

    check(args.namespace, args.appid)
    database = args.db or f"{re.sub(r'[^a-z0-9]', '', args.name.lower()) or 'app'}.db"

    plan = [
        ("namespace", TEMPLATE_NAMESPACE, args.namespace),
        ("applicationId", TEMPLATE_APP_ID, args.appid),
        ("app name", TEMPLATE_NAME, args.name),
        ("database", "app.db", database),
    ]
    print("bootstrap will apply:")
    for label, old, new in plan:
        print(f"  {label:14} {old}  ->  {new}")
    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    # --- Kotlin -------------------------------------------------------------------------------
    move_sources(args.namespace)
    kotlin_replacements = [(TEMPLATE_NAMESPACE, args.namespace)]
    touched = 0
    for path in ROOT.rglob("*.kt"):
        if "build/" in str(path.relative_to(ROOT)):
            continue
        touched += rewrite(path, kotlin_replacements)
    print(f"\nrewrote {touched} Kotlin files")

    # --- Gradle -------------------------------------------------------------------------------
    rewrite(
        ROOT / "app/build.gradle.kts",
        [
            (f'namespace = "{TEMPLATE_NAMESPACE}"', f'namespace = "{args.namespace}"'),
            (f'applicationId = "{TEMPLATE_APP_ID}"', f'applicationId = "{args.appid}"'),
        ],
    )

    # --- The toolchain's own copies -----------------------------------------------------------
    rewrite(
        ROOT / "scripts/project.py",
        [
            (f'APP_NAME = "{TEMPLATE_NAME}"', f'APP_NAME = "{args.name}"'),
            ('DATABASE_FILE = "app.db"', f'DATABASE_FILE = "{database}"'),
        ],
    )
    rewrite(ROOT / "scripts/gen_scheme.py", [(f'PACKAGE = "{TEMPLATE_NAMESPACE}"', f'PACKAGE = "{args.namespace}"')])
    rewrite(ROOT / "art/make-feature-graphic.py", [(f'APP_NAME = "{TEMPLATE_NAME}"', f'APP_NAME = "{args.name}"')])

    # --- Resources ----------------------------------------------------------------------------
    for strings in ROOT.glob("app/src/*/res/values*/strings.xml"):
        rewrite(strings, [(f'"app_name" translatable="false">{TEMPLATE_NAME}<', f'"app_name" translatable="false">{args.name}<')])
    rewrite(ROOT / "app/src/main/java" / args.namespace.replace(".", "/") / "data/AppDatabase.kt",
            [('APP_DATABASE_FILE = "app.db"', f'APP_DATABASE_FILE = "{database}"')])
    rewrite(ROOT / "app/src/main/java" / args.namespace.replace(".", "/") / "data/backup/BackupManifest.kt",
            [('DATABASE_ENTRY = "database/app.db"', f'DATABASE_ENTRY = "database/{database}"')])

    # --- Exported schemas move with the database class ------------------------------------------
    schemas = ROOT / "app/schemas"
    old_schema_dir = schemas / f"{TEMPLATE_NAMESPACE}.data.AppDatabase"
    if old_schema_dir.is_dir():
        shutil.move(str(old_schema_dir), str(schemas / f"{args.namespace}.data.AppDatabase"))

    # --- Release automation ---------------------------------------------------------------------
    config = ROOT / "release-please-config.json"
    if config.is_file():
        data = json.loads(config.read_text())
        data["packages"]["."]["package-name"] = ROOT.name
        # `bootstrap-sha` names a commit in *this* template's history. Left behind, release-please
        # would look for a commit the new repository does not contain.
        data.pop("bootstrap-sha", None)
        config.write_text(json.dumps(data, indent=2) + "\n")
    (ROOT / ".release-please-manifest.json").write_text('{\n  ".": "0.1.0"\n}\n')
    (ROOT / "CHANGELOG.md").write_text(f"# Changelog\n\nNothing released yet.\n")

    rewrite(ROOT / "docs/_config.yml", [("title: Starter", f"title: {args.name}")])

    # --- Everywhere the applicationId is stated outside Gradle ----------------------------------
    # These are not derived at build time on purpose: a wrong value uploads to a *different* Play
    # app entry rather than failing, so each one is stated explicitly and rewritten here.
    for path in [
        ROOT / "fastlane/Appfile",
        ROOT / ".github/workflows/publish-play.yml",
        ROOT / ".github/workflows/publish-play-production.yml",
    ]:
        rewrite(path, [(TEMPLATE_APP_ID, args.appid)])

    # --- Store listing --------------------------------------------------------------------------
    rewrite(ROOT / "docs/store-listing.md", [(f"\n{TEMPLATE_NAME}\n", f"\n{args.name}\n")])

    # --- Claude Code ------------------------------------------------------------------------------
    # Merged rather than overwritten, in case the new repository already carries settings of its own.
    settings_file = ROOT / ".claude/settings.json"
    settings = json.loads(settings_file.read_text()) if settings_file.is_file() else {}
    pre_tool_use = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])
    if PUSH_HOOK not in pre_tool_use:
        pre_tool_use.append(PUSH_HOOK)
    settings_file.parent.mkdir(exist_ok=True)
    settings_file.write_text(json.dumps(settings, indent=2) + "\n")
    print("claude: .claude/settings.json now runs notes-gate.py --pending before every git push")

    # --- Git ------------------------------------------------------------------------------------
    if args.fresh_git:
        shutil.rmtree(ROOT / ".git", ignore_errors=True)
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=ROOT, check=True)
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", f"feat: scaffold {args.name} from the Android starter template"],
            cwd=ROOT,
            check=True,
        )
        print("git: fresh history, one commit")
    elif not args.keep_git:
        print("git: left alone (pass --fresh-git to start a new history)")

    print(
        "\nDone. Next:\n"
        "  git config core.hooksPath .githooks     # Conventional Commits, which release-please needs\n"
        "  ./gradlew assembleDebug test\n"
        f"  python3 scripts/gen_scheme.py > app/src/main/java/{args.namespace.replace('.', '/')}/theme/Color.kt\n"
        "  $EDITOR art/mark.py && python3 art/make-launcher-icon.py\n"
        "  rm bootstrap.py\n"
        "  commit .claude/settings.json, and start Claude Code *inside* this directory - it reads\n"
        "  project hooks only from the folder it was launched in"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
