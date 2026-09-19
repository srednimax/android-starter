#!/usr/bin/env python3
"""Diff two backups and prove an upgrade lost nothing.

    python3 scripts/upgrade-diff.py before.zip after.zip

This is the reading half of the standing schema gate's item 5 — "an actual
upgrade watched on the phone" (docs/DOD.md) — and it exists because the Play
install cannot be read any other way. A release build is not debuggable, so
`adb shell run-as <pkg>` is refused and the database cannot be pulled. The app's
own backup export is the only route to those rows, and it is a faithful one:
the archive carries the *raw* database, and BackupExporter checkpoints the WAL
before it zips (verified against a shipped build, not just on main).

What it asserts, in the order the failures actually happen:

  1. user_version climbed. A database that did not migrate cannot have lost
     anything, and reporting "no differences" about it would be a lie of
     omission.
  2. No table vanished.
  3. Every row of every surviving table is still there, compared on the
     columns the two schemas share. Added columns are not a loss; a dropped
     column is not compared, which is why 4 exists.
  4. Every column a migration *moves* off a table arrived in the table that
     replaced it — the entries in COLUMN_MOVES below, empty until your first
     migration moves one. A generic column diff cannot see any of them — the
     column is gone from one side of the comparison by definition — so each one
     is declared by hand, in the same commit as the migration that moves it.
  5. Media files survived. "An update never loses an owner's data" is not
     only about rows.

The cascade trap is why 3 matters more than it looks. A migration that rebuilds
a parent table by create-copy-drop-rename fires every child table's ON DELETE
CASCADE at the `DROP TABLE`. Room's runMigrationsAndValidate passes happily on the
wreckage: a database whose every child row has been cascaded away still has
exactly the right *schema*. The app this template came from met exactly this.
Only a row count can tell you, and only against a before-image.

Exits non-zero if anything was lost. Prints and exits 0 if nothing was.
"""

import collections
import os
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project  # noqa: E402  — the path insert above has to come first

# Where BackupExporter puts the database inside the zip — `DATABASE_ENTRY` in
# data/backup/BackupManifest.kt. Derived from project.py rather than written out,
# because bootstrap.py renames the database and a literal "app.db" here would then
# refuse every real backup as "not one of this app's".
DB_ENTRY = f"database/{project.DATABASE_FILE}"

# Room's bookkeeping table carries the schema identity hash, which is *supposed*
# to differ between two versions. Comparing it would fail every honest upgrade.
IGNORED_TABLES = {"room_master_table", "android_metadata", "sqlite_sequence"}

# The non-generic assertions: every place a migration *moved* a column off a
# table rather than dropping it. Check 3 is blind to these by definition — the
# column is gone from one side of the comparison, so a generic diff has nothing
# to compare. Empty until a migration moves one; add the entry in the same
# commit as the migration.
#
# (source_table, before_column, after_table, after_key_column, after_value_column, migration)
#
# The typical shape is a single-valued column becoming a child table — one photo
# path becoming a table of photos — so the old value must be *among* what landed
# under the same parent id, not equal to all of it. For example:
#
#     ("items", "photoPath", "item_photos", "itemId", "path", "MIGRATION_2_3"),
#
# Enums are stored by name and never by ordinal (CLAUDE.md), so a value migrates
# as itself with no translation, and the comparison is plain equality.
COLUMN_MOVES: list[tuple[str, str, str, str, str, str]] = []


def fail(message):
    print(f"\n{message}", file=sys.stderr)
    sys.exit(1)


def extract_db(zip_path, into):
    """Pull the database out of a backup, WAL included if one is there.

    BackupExporter checkpoints before zipping, so a well-formed archive has no
    -wal member at all. The handling is here anyway because a *stale* read is
    the failure that looks exactly like a pass: a deleted row once read back as
    present from a database pulled without its -wal sibling.
    """
    try:
        archive = zipfile.ZipFile(zip_path)
    except FileNotFoundError:
        fail(f"no such backup: {zip_path}")
    except zipfile.BadZipFile:
        fail(f"not a zip archive: {zip_path}")

    with archive:
        names = archive.namelist()
        if DB_ENTRY not in names:
            fail(f"{zip_path} has no {DB_ENTRY} — is it one of this app's backups?")

        target = os.path.join(into, project.DATABASE_FILE)
        with archive.open(DB_ENTRY) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)

        for suffix in ("-wal", "-shm"):
            member = DB_ENTRY + suffix
            if member in names:
                print(f"  note: {os.path.basename(zip_path)} carries a {suffix} member; "
                      "checkpointing it in")
                with archive.open(member) as src, open(target + suffix, "wb") as dst:
                    shutil.copyfileobj(src, dst)

        media = sorted(
            n for n in names
            if not n.startswith(("database/", "preferences/")) and not n.endswith("/")
            and n != "manifest.json"
        )

    # Harmless when there was no WAL, and the whole point when there was.
    connection = sqlite3.connect(target)
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    connection.close()

    return target, media


def tables(connection):
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {r[0] for r in rows} - IGNORED_TABLES


def columns(connection, table):
    return [r[1] for r in connection.execute(f'PRAGMA table_info("{table}")')]


def stringly(counter):
    """The same rows with every value flattened to text, for the affinity check."""
    return collections.Counter(
        tuple(None if v is None else str(v) for v in row)
        for row in counter.elements()
    )


def rows_of(connection, table, cols):
    quoted = ", ".join(f'"{c}"' for c in cols)
    return collections.Counter(
        connection.execute(f'SELECT {quoted} FROM "{table}"').fetchall()
    )


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__.strip().splitlines()[2].strip())

    before_zip, after_zip = sys.argv[1], sys.argv[2]

    with tempfile.TemporaryDirectory() as workdir:
        before_dir = os.path.join(workdir, "before")
        after_dir = os.path.join(workdir, "after")
        os.makedirs(before_dir)
        os.makedirs(after_dir)

        before_db, before_media = extract_db(before_zip, before_dir)
        after_db, after_media = extract_db(after_zip, after_dir)

        before = sqlite3.connect(before_db)
        after = sqlite3.connect(after_db)

        losses = []

        # 1 — the migration actually ran.
        v_before = before.execute("PRAGMA user_version").fetchone()[0]
        v_after = after.execute("PRAGMA user_version").fetchone()[0]
        print(f"user_version   {v_before} -> {v_after}")
        if v_after <= v_before:
            losses.append(
                f"user_version did not climb ({v_before} -> {v_after}). Nothing migrated, "
                "so this comparison proves nothing about migrating."
            )

        # 2 and 3 — every table, and every row of it, on the columns they share.
        t_before, t_after = tables(before), tables(after)

        vanished = sorted(t_before - t_after)
        for table in vanished:
            losses.append(f"table `{table}` exists in {before_zip} and is gone from {after_zip}")

        added = sorted(t_after - t_before)
        print(f"tables         {len(t_before)} -> {len(t_after)}"
              + (f", new: {', '.join(added)}" if added else ""))
        print()

        for table in sorted(t_before & t_after):
            c_before, c_after = columns(before, table), columns(after, table)
            common = [c for c in c_before if c in c_after]
            dropped = [c for c in c_before if c not in c_after]
            gained = [c for c in c_after if c not in c_before]

            if not common:
                losses.append(f"table `{table}` shares no columns between the two schemas")
                continue

            r_before = rows_of(before, table, common)
            r_after = rows_of(after, table, common)
            missing = r_before - r_after
            reshaped = None

            if missing:
                # A row can also "go missing" by keeping its value and changing its
                # *type*: SQLite applies the destination column's affinity on copy, so
                # a rebuild that declares `recordedAt` TEXT turns 1782835200000 into
                # '1782835200000' and every row stops matching. That is a real defect
                # and worth failing on — but it is not loss, and reporting it as
                # "5 rows absent" next to a "5 -> 5" count sends the reader hunting
                # for rows that are all still there.
                missing = stringly(r_before) - stringly(r_after)
                reshaped = not missing

            note = ""
            if dropped:
                note += f"  −{','.join(dropped)}"
            if gained:
                note += f"  +{','.join(gained)}"

            n_before, n_after = sum(r_before.values()), sum(r_after.values())
            status = "LOST" if missing else ("TYPE" if reshaped else "ok  ")
            print(f"  {status} {table:34} {n_before:5} -> {n_after:<5} "
                  f"on {len(common)} common columns{note}")

            if missing:
                losses.append(
                    f"{sum(missing.values())} row(s) of `{table}` present before and absent after; "
                    f"first: {next(iter(missing))!r}"
                )
            elif reshaped:
                losses.append(
                    f"every row of `{table}` survived but at least one column changed type "
                    "affinity — the values are equal as text and unequal as stored. Check the "
                    "column types the migration declares against the exported schema JSON."
                )

        # 4 — the columns that moved rather than vanished.
        print()
        # Which moves this particular upgrade is even on the hook for: a jump that
        # starts after a move never had the old column to move. Asking the before
        # image is what tells them apart.
        due = [
            move for move in COLUMN_MOVES
            if move[0] in t_before and move[1] in columns(before, move[0])
        ]

        for source, column, destination, key_column, value_column, migration in due:
            if destination not in t_after:
                losses.append(
                    f"`{source}.{column}` was dropped and `{destination}` does not exist"
                )
                continue

            staged = before.execute(
                f'SELECT id, "{column}" FROM "{source}" WHERE "{column}" IS NOT NULL'
            ).fetchall()

            landed = collections.Counter(
                after.execute(
                    f'SELECT "{key_column}", "{value_column}" FROM "{destination}"'
                ).fetchall()
            )
            # A destination may be multi-valued, so a single old value must be
            # *among* what landed, not equal to all of it.
            lost = [pair for pair in staged if landed[pair] == 0]

            status = "ok  " if not lost else "LOST"
            print(f"  {status} {source}.{column:18} {len(staged):5} value(s) "
                  f"-> {destination}")
            if lost:
                losses.append(
                    f"{len(lost)} value(s) of `{source}.{column}` did not arrive in "
                    f"`{destination}` ({migration}); first: {lost[0]!r}"
                )

        if not due:
            print("  ·    the before image holds no column any migration moves")

        # 5 — media is data too.
        print()
        lost_media = sorted(set(before_media) - set(after_media))
        status = "ok  " if not lost_media else "LOST"
        print(f"  {status} media files                        "
              f"{len(before_media):5} -> {len(after_media):<5}")
        if lost_media:
            losses.append(f"{len(lost_media)} media file(s) missing after, first: {lost_media[0]}")

        before.close()
        after.close()

    print()
    if losses:
        # Not "lost data": a migration that never ran and a column that changed
        # affinity are both failures worth stopping for, and neither is a loss.
        print(f"{len(losses)} problem(s) with this upgrade:", file=sys.stderr)
        for problem in losses:
            print(f"  - {problem}", file=sys.stderr)
        print("\nDo not promote this build.", file=sys.stderr)
        return 1

    print(f"nothing lost: {v_before} -> {v_after}, every row of every surviving table "
          "still present on shared columns")
    return 0


if __name__ == "__main__":
    sys.exit(main())
