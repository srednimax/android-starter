#!/usr/bin/env python3
"""The translation gate: a branch merges with every shipped language complete, and not before.

Run by CI on every pull request, and worth running by hand while you work:

    python3 scripts/translation-gate.py --report      # what do I owe so far?
    python3 scripts/translation-gate.py origin/main   # would this merge?

**Why this is a gate and not a test.** "Every base string has a counterpart in every locale" used to
be an assertion in `TranslationTest`, which made a missing translation a red build the moment the
English string was written. That is the right rule at the wrong boundary: at nine languages it puts
every feature branch behind a translation round, so copy gets translated against the draft wording
and then again after review reworded it — nine times, for nothing. ADR-0013's promise is about what
*ships*, not about what a working tree looks like on a Tuesday.

So the boundary moved rather than the rule: **free while you work, strict before it merges.**
Everything that must hold for whatever is already translated — format arguments, plural categories,
orphans, untranslatable resources — stays in `TranslationTest` and stays green continuously.

Three things fail this gate:

  1. **Missing** — a translatable base resource with no counterpart in a shipped locale. Reported
     split by whether this branch introduced it, because that is the list you actually have to write
     and the rest is a pre-existing debt you probably did not cause.
  2. **Stale** — the English changed on this branch and the translation did not. A translation that
     still parses and still carries its format arguments but now says something the English no
     longer says is invisible to every other check in this repo.
  3. **Orphaned** — a locale declares something the base language does not. Cheap to catch here too,
     and it is what a rename leaves behind.

And a fourth that is not about the translations at all: **an unusable comparison**. Missing and
orphaned are read off the working tree, but stale needs a merge base, and without one it does not
fail — it disappears. So no merge base is itself a failure, rather than a quiet downgrade to the two
checks that still work.

Drafts staged in `translations/<tag>/` are **reported and never gated**. A language that is not in
`locales_config.xml` is offered to nobody, so its completeness cannot block a merge — but it is the
one number nothing else prints, since `TranslationTest` checks a draft's correctness and says
nothing about how much of it exists yet.

What it deliberately does not check: whether the translation is any *good*. A language ships on a
native speaker's read-through (`docs/translator-brief.md` §8), and no script stands in for that.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "app/src/main/res"
BASE_STRINGS = RES / "values/strings.xml"
LOCALES_CONFIG = RES / "xml/locales_config.xml"
STAGED = ROOT / "translations"
BASE_LOCALE = "en"

STRING = re.compile(r'<string\s+name="([^"]+)"([^>]*)>(.*?)</string>', re.S)
PLURALS = re.compile(r'<plurals\s+name="([^"]+)"([^>]*)>(.*?)</plurals>', re.S)
ARRAY = re.compile(r'<string-array\s+name="([^"]+)"([^>]*)>(.*?)</string-array>', re.S)
LOCALE_ENTRY = re.compile(r'<locale\s+android:name="([^"]+)"')


def qualifier(tag: str) -> str:
    """The `values-` qualifier for a BCP-47 tag: `pl` -> `pl`, `pt-BR` -> `pt-rBR`."""
    parts = tag.split("-")
    return f"{parts[0]}-r{parts[1]}" if len(parts) == 2 else tag


def strings_path(tag: str) -> Path:
    return RES / "values" / "strings.xml" if tag == BASE_LOCALE else RES / f"values-{qualifier(tag)}/strings.xml"


def parse(text: str) -> tuple[dict[str, str], set[str]]:
    """Resource name -> its value, plus the names marked `translatable="false"`.

    Plurals and arrays collapse to their whole inner text. That is deliberate: this gate asks
    whether a resource is *present* and whether it has *moved*, and the inner text answers both.
    Category-by-category correctness is `TranslationTest`'s job.
    """
    values: dict[str, str] = {}
    untranslatable: set[str] = set()
    for pattern in (STRING, PLURALS, ARRAY):
        for name, attributes, body in pattern.findall(text):
            values[name] = " ".join(body.split())
            if 'translatable="false"' in attributes:
                untranslatable.add(name)
    return values, untranslatable


def at_ref(ref: str, path: Path) -> str | None:
    """A file's contents as of `ref`, or None when it did not exist there."""
    shown = subprocess.run(
        ["git", "show", f"{ref}:{path.relative_to(ROOT)}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return shown.stdout if shown.returncode == 0 else None


def merge_base(ref: str) -> str | None:
    found = subprocess.run(
        ["git", "merge-base", "HEAD", ref],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    # Empty output counts as failure too, not just a non-zero exit: both mean "no common ancestor",
    # and an empty string would sail through a truthiness check further down.
    if found.returncode != 0:
        return None
    return found.stdout.strip() or None


def shipped_locales() -> list[str]:
    return LOCALE_ENTRY.findall(LOCALES_CONFIG.read_text())


def staged_locales() -> list[str]:
    """Drafts waiting outside `res/`, one directory per BCP-47 tag (Phase 8)."""
    if not STAGED.is_dir():
        return []
    return sorted(child.name for child in STAGED.iterdir() if (child / "strings.xml").is_file())


def outstanding(translated: dict[str, str], translatable: dict[str, str], current: dict[str, str]) -> tuple[list[str], list[str]]:
    """What one locale is missing, and what it declares that the base language does not."""
    return sorted(set(translatable) - set(translated)), sorted(set(translated) - set(current))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", nargs="?", default="origin/main", help="branch to compare against")
    parser.add_argument(
        "--report",
        action="store_true",
        help="list what is outstanding and exit 0 — for use while the work is still in progress",
    )
    args = parser.parse_args()

    current, untranslatable = parse(BASE_STRINGS.read_text())
    translatable = {name: value for name, value in current.items() if name not in untranslatable}

    locales = [tag for tag in shipped_locales() if tag != BASE_LOCALE]
    if not locales:
        print("translation-gate: English only, nothing to translate against.")
        return 0

    # What this branch did to the base language — which needs a merge base, and refuses to guess
    # without one.
    #
    # This used to fall back to an empty `previous`, on the reasoning that reading every string as
    # pre-existing is "the safe way round". It is not. It is safe for *missing* (those are still
    # demanded) and silently fatal for *stale*, which is computed only from `reworded` and so
    # becomes an unconditional no-op. CI ran that way: a depth-1 checkout of the PR merge ref
    # against a shallow `main` share no ancestor, `git merge-base` exits 1, and a reworded English
    # string whose translation had not followed passed green. A gate that cannot make its
    # comparison must fail, not pass — the whole point is that nothing else in this repo catches it.
    point = merge_base(args.base)
    if point is None:
        unusable = (
            f"translation-gate: no merge base between HEAD and {args.base}. Nothing to compare "
            "against, so the stale check cannot run — refusing to pass on a comparison that did "
            "not happen. In CI this means the checkout is shallow: use fetch-depth: 0 and fetch "
            f"the base branch without --depth. Locally, `git fetch origin {args.base.split('/')[-1]}`."
        )
        if not args.report:
            print(unusable, file=sys.stderr)
            return 1
        print(f"{unusable}\nReporting what can still be checked.\n", file=sys.stderr)

    previous_text = at_ref(point, BASE_STRINGS) if point else None
    previous, _ = parse(previous_text) if previous_text is not None else ({}, set())

    added = {name for name in translatable if name not in previous} if previous else set()
    reworded = {
        name for name, value in translatable.items() if name in previous and previous[name] != value
    }

    problems: list[str] = []
    for tag in locales:
        path = strings_path(tag)
        if not path.is_file():
            problems.append(f"values-{qualifier(tag)}/strings.xml does not exist, but {tag} is shipped")
            continue

        translated, _ = parse(path.read_text())
        missing, orphaned = outstanding(translated, translatable, current)

        # Stale: the English moved on this branch and the translation did not follow it. Checked
        # against the translation's own previous text rather than against "did the file change",
        # so an unrelated edit elsewhere in the file cannot vouch for this string.
        was_text = at_ref(point, path) if point else None
        was, _ = parse(was_text) if was_text is not None else ({}, set())
        stale = sorted(
            name
            for name in reworded
            if name in translated and name in was and was[name] == translated[name]
        )

        label = f"values-{qualifier(tag)}"
        if missing:
            new_here = [name for name in missing if name in added]
            standing = [name for name in missing if name not in added]
            if new_here:
                problems.append(f"{label}: {len(new_here)} added on this branch and not translated")
                problems.extend(f"    + {name}" for name in new_here)
            if standing:
                problems.append(f"{label}: {len(standing)} missing from before this branch")
                problems.extend(f"    · {name}" for name in standing)
        if stale:
            problems.append(f"{label}: {len(stale)} whose English changed here but translation did not")
            problems.extend(f"    ~ {name}" for name in stale)
        if orphaned:
            problems.append(f"{label}: {len(orphaned)} declared here but not in the base language")
            problems.extend(f"    ? {name}" for name in orphaned)

    # Staged drafts are reported and never gated. A draft is work in progress by definition, and
    # the merge rule is about what *ships* — a language that is not in locales_config.xml is not
    # offered to anyone. What is worth printing is how far one still has to go, which is the only
    # place that number is visible: `TranslationTest` checks a draft's correctness and says nothing
    # about its completeness.
    drafts: list[str] = []
    for tag in staged_locales():
        if tag in locales:
            drafts.append(
                f"translations/{tag}: also shipped as values-{qualifier(tag)} — "
                "promotion is a move, not a copy"
            )
            continue
        translated, _ = parse((STAGED / tag / "strings.xml").read_text())
        missing, orphaned = outstanding(translated, translatable, current)
        drafts.append(f"translations/{tag}: {len(translatable) - len(missing)}/{len(translatable)} translated")
        drafts.extend(f"    · {name}" for name in missing)
        drafts.extend(f"    ? {name} — not in the base language" for name in orphaned)

    def report_drafts(stream) -> None:
        if not drafts:
            return
        print("\nStaged drafts, not shipped and not gated:", file=stream)
        for draft in drafts:
            print(f"  {draft}" if draft.startswith("    ") else f"  › {draft}", file=stream)

    scope = f"{len(translatable)} translatable resources × {len(locales)} locale(s)"
    if not problems:
        print(f"translation-gate: {scope} — complete, and nothing stale.")
        report_drafts(sys.stdout)
        return 0

    stream = sys.stdout if args.report else sys.stderr
    headline = "still outstanding" if args.report else "this branch cannot merge yet"
    print(f"translation-gate: {scope} — {headline}:", file=stream)
    for problem in problems:
        print(f"  {problem}" if problem.startswith("    ") else f"  ✗ {problem}", file=stream)
    report_drafts(stream)

    if args.report:
        print(
            f"\n{len(added)} resource(s) added and {len(reworded)} reworded on this branch. "
            "Reported only — run without --report for the gate's own verdict.",
            file=stream,
        )
        return 0

    print(
        "\nA language ships complete or not at all (ADR-0013). Draft against "
        "docs/translator-brief.md, and use --report while the work is still moving.",
        file=stream,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
