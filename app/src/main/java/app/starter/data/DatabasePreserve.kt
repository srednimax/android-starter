package app.starter.data

import java.io.File
import java.io.RandomAccessFile
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

/** Where preserved copies land, relative to `filesDir` — alongside the media directories. */
const val PRESERVED_DIRECTORY = "preserved"

/** How a preserved copy is named. Settings matches on these to find them again. */
internal const val PRESERVED_PREFIX = "db-"
internal const val PRESERVED_SUFFIX = ".db"

/**
 * How a **pre-restore snapshot** is named (ADR-0005) — the other occupant of `preserved/`, and the
 * one with the opposite properties: current schema, restorable in one tap, where a wipe copy is at a
 * stale schema and unrestorable by design.
 *
 * Named for what it is rather than for its scope, so a listing can say which row is which. It sits
 * beside the wipe copies deliberately: `preserved/` is the directory this app never prunes, and both
 * occupants are recovery artifacts.
 */
internal const val SNAPSHOT_PREFIX = "before-restore-"
internal const val SNAPSHOT_SUFFIX = ".zip"

/**
 * In WAL mode the most recent writes may live only in a sidecar, so a copy of the `.db` alone can be
 * missing the very data worth preserving. Both travel with it, and both have to travel again when
 * the owner shares the copy off the phone.
 */
internal val PRESERVED_SIDECAR_SUFFIXES = listOf("-wal", "-shm")

/**
 * SQLite writes `user_version` as a big-endian 32-bit integer at byte 60 of the 100-byte file
 * header, and Room uses that field as its schema version. Reading it is therefore a four-byte read
 * that needs neither Room nor SQLite — which is the whole point: it has to happen *before* Room
 * opens the file and wipes it.
 */
private const val USER_VERSION_OFFSET = 60L
private const val SQLITE_HEADER_BYTES = 100

/**
 * Filesystem-safe and sorts chronologically. Colons in a filename are a portability trap.
 *
 * `internal` rather than private because Settings reads the date back *out* of the filename when it
 * lists the copies — the name dates the data, where the copy's own `lastModified` only dates the
 * moment it was written.
 */
internal val PRESERVED_TIMESTAMP_FORMAT: DateTimeFormatter =
    DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss'Z'").withZone(ZoneOffset.UTC)

/**
 * Reads the schema version recorded in [databaseFile]'s header.
 *
 * Returns 0 for a file that does not exist, is empty, or is too short to hold a header — all of
 * which mean "there is nothing here to lose", which is exactly how a fresh install looks.
 */
fun readUserVersion(databaseFile: File): Int {
    if (!databaseFile.isFile || databaseFile.length() < SQLITE_HEADER_BYTES) return 0
    return RandomAccessFile(databaseFile, "r").use { file ->
        file.seek(USER_VERSION_OFFSET)
        file.readInt() // RandomAccessFile.readInt is big-endian, which matches the header
    }
}

/**
 * Whether the file on disk is at a version this build cannot simply open — the one rule behind both
 * things that have to know it, stated once.
 *
 * `0` is "there is nothing here": no file, an empty one, or one too short to hold a header, which is
 * exactly how a fresh install looks. A **newer** on-disk version counts as pending too, because Room
 * destroys a downgrade just as thoroughly as it destroys an upgrade.
 *
 * Two callers, arrived at from opposite directions. [preserveBeforeWipe] asks it to decide whether
 * there is anything worth copying aside. The daily sweep asks it because it runs with no UI and no user
 * present, and **any worker that touches a repository forces the container**. A sweep that ran
 * anyway would destroy a database in the background, on a phone nobody is looking at.
 */
fun schemaMismatchPending(
    onDiskVersion: Int,
    appSchemaVersion: Int = APP_SCHEMA_VERSION,
): Boolean = onDiskVersion != 0 && onDiskVersion != appSchemaVersion

/**
 * Copies the database aside if opening it with this build would destroy it, and returns the copy.
 * Returns null when there is nothing to preserve — no file yet, or a file already at this version.
 *
 * ADR-0001: a destructive wipe never loses the file. Its **consent** half — the blocking screen in
 * front of this — is wired up by `MainApplication`, which is where this runs: before Room exists,
 * let alone opens anything.
 *
 * The copy is named from the database file's own [File.lastModified] rather than the moment of
 * panic, so a hesitating user who relaunches repeatedly **overwrites one copy instead of minting a
 * new one each time** — nothing has written to the file in between, so its modification time has not
 * moved. The name therefore dates the *data*, not the launch. [timestamp] stays a parameter only so
 * tests can pin it.
 *
 * The preserved file is a **recovery artifact, not a restore**: reading old data into a new schema
 * *is* a migration, so it cannot be re-imported automatically.
 */
fun preserveBeforeWipe(
    databaseFile: File,
    preservedDir: File,
    appSchemaVersion: Int = APP_SCHEMA_VERSION,
    timestamp: Instant = Instant.ofEpochMilli(databaseFile.lastModified()),
): File? {
    if (!schemaMismatchPending(readUserVersion(databaseFile), appSchemaVersion)) return null

    preservedDir.mkdirs()
    val preserved =
        File(preservedDir, "$PRESERVED_PREFIX${PRESERVED_TIMESTAMP_FORMAT.format(timestamp)}$PRESERVED_SUFFIX")
    databaseFile.copyTo(preserved, overwrite = true)

    for (suffix in PRESERVED_SIDECAR_SUFFIXES) {
        val sidecar = File(databaseFile.path + suffix)
        if (sidecar.isFile) sidecar.copyTo(File(preserved.path + suffix), overwrite = true)
    }
    return preserved
}
