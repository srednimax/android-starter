#!/usr/bin/env python3
"""The schema gate: a bump to APP_SCHEMA_VERSION must arrive with its migration and its proof.

Run by CI on every pull request, and worth running by hand before opening one:

    python3 scripts/schema-gate.py origin/main

The rule this enforces is the one an owner cares about: **an update never loses data.** A schema
version that climbs without a registered migration turns every existing install into either a wipe
(debug) or a refusal screen (release), and neither is discovered by any test that opens the database
directly — which is every migration test this project has. So the gate is mechanical rather than
remembered.

For each step between the base branch's schema version and this branch's, it requires:

  1. `app/schemas/<version>.json` — the exported shape, committed, because every later migration is
     written from it (ADR-0007).
  2. `MIGRATION_<from>_<to>` in `Migrations.kt`, *and* its presence in `APP_MIGRATIONS` — a
     migration that exists but is not registered is not a migration Room will ever run.
  3. `SchemaGateTest` asserting the new version, so the launch gate is proven to let the upgrade
     through rather than showing the refusal screen (ADR-0023's Phase 7.5 amendment).

What it deliberately does not check: that the migration is *correct*. That is what the committed
backup fixtures and the instrumented `MigrationTestHelper` runs are for, and no script can stand in
for a real archive written by a shipped build.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project  # noqa: E402  — the path insert above has to come first

ROOT = project.ROOT
DATABASE = project.MAIN_SRC / "data/AppDatabase.kt"
MIGRATIONS = project.MAIN_SRC / "data/Migrations.kt"
GATE_TEST = project.TEST_SRC / "data/SchemaGateTest.kt"
SCHEMAS = ROOT / "app/schemas"

VERSION = re.compile(rf"const val {project.SCHEMA_VERSION_CONST}\s*=\s*(\d+)")


def version_in(text: str) -> int | None:
    found = VERSION.search(text)
    return int(found.group(1)) if found else None


def version_at(ref: str) -> int | None:
    """The schema version as of `ref`, or None when the file is not there (a very old base)."""
    path = DATABASE.relative_to(ROOT)
    shown = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return version_in(shown.stdout) if shown.returncode == 0 else None


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"

    current = version_in(DATABASE.read_text())
    if current is None:
        print(f"schema-gate: could not read {project.SCHEMA_VERSION_CONST} from {DATABASE}", file=sys.stderr)
        return 1

    previous = version_at(base)
    if previous is None:
        print(f"schema-gate: no {project.SCHEMA_VERSION_CONST} at {base}; nothing to compare, passing.")
        return 0

    if current == previous:
        print(f"schema-gate: schema unchanged at {current}. Nothing to prove.")
        return 0

    if current < previous:
        print(
            f"schema-gate: schema went DOWN, {previous} → {current}. No migration runs backwards, so "
            "every install that already wrote the higher version would be refused at launch.",
            file=sys.stderr,
        )
        return 1

    migrations = MIGRATIONS.read_text()
    gate_test = GATE_TEST.read_text() if GATE_TEST.is_file() else ""
    registered = re.search(rf"{project.MIGRATIONS_CONST}[^\n]*=\s*arrayOf\(([^)]*)\)", migrations)
    registered_names = registered.group(1) if registered else ""

    problems: list[str] = []

    for step in range(previous, current):
        name = f"MIGRATION_{step}_{step + 1}"
        if not re.search(rf"val {name}\b", migrations):
            problems.append(f"{name} is not written in Migrations.kt")
        elif name not in registered_names:
            problems.append(f"{name} exists but is not in {project.MIGRATIONS_CONST} — Room will never run it")

    # Room exports under a directory named for the database class, so glob rather than assume.
    if not list(SCHEMAS.glob(f"*/{current}.json")):
        problems.append(f"app/schemas/*/{current}.json is missing — export and commit it (ADR-0007)")

    if f"appSchemaVersion = {current}" not in gate_test:
        problems.append(
            f"SchemaGateTest does not assert appSchemaVersion = {current} — the launch gate is "
            "unproven for this bump, which is exactly how 1.5 nearly shipped a refusal screen"
        )

    if problems:
        print(f"schema-gate: schema {previous} → {current}, and the proof is incomplete:", file=sys.stderr)
        for problem in problems:
            print(f"  ✗ {problem}", file=sys.stderr)
        print(
            "\nAn update must migrate an existing install without losing anything. See ADR-0007, "
            "ADR-0023 and docs/DOD.md's standing schema gate.",
            file=sys.stderr,
        )
        return 1

    print(f"schema-gate: schema {previous} → {current}, migration registered, shape exported, gate asserted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
