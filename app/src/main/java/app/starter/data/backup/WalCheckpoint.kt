package app.starter.data.backup

import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteException
import java.io.File

/**
 * Copy [databaseFile] to [target] with its write-ahead log folded in first.
 *
 * Room runs in WAL mode, so the most recent committed writes may live only in the `-wal` sidecar.
 * Copying the `.db` alone therefore hands over a file that is missing the very data the user asked
 * to keep — and copying the sidecars alongside it is the other half of the same trap, because a
 * `-wal` captured mid-write restores corrupt. Checkpointing collapses the log into the main file,
 * after which the `.db` is the whole database on its own and the sidecars are irrelevant.
 *
 * `TRUNCATE` rather than `PASSIVE`: a passive checkpoint gives up quietly when a reader is in the
 * way, which would leave exactly the silently-incomplete copy this exists to prevent.
 *
 * **The export and the backup agent share this** (ADR-0005). An export that captures a mid-write
 * database is the same bug as a backup that does, and writing it once, here, is what lets a test
 * watch it happen rather than waiting for a phone to be idle and charging.
 *
 * ⚠️ This is also the trap on the *reading* side: a database file pulled off a device with `adb` and
 * without its `-wal` sidecar is **stale**, so a row you just deleted still reads as present. Pull
 * both, or checkpoint first.
 *
 * Opening a second connection alongside Room's own is safe — that is what SQLite's locking is for —
 * and takes no `Context`, so the agent can call it.
 */
fun checkpointDatabaseTo(
    databaseFile: File,
    target: File,
) {
    if (databaseFile.isFile) {
        try {
            SQLiteDatabase
                .openDatabase(databaseFile.path, null, SQLiteDatabase.OPEN_READWRITE)
                .use { database ->
                    // A PRAGMA that returns rows has to be run as a query; `execSQL` would refuse it.
                    database.rawQuery("PRAGMA wal_checkpoint(TRUNCATE)", null).use { it.moveToFirst() }
                }
        } catch (e: SQLiteException) {
            // A checkpoint that could not run is not a reason to refuse the export. The copy below
            // still carries everything committed before the last checkpoint, which is strictly more
            // than refusing would leave the user with.
        }
    }
    target.parentFile?.mkdirs()
    databaseFile.copyTo(target, overwrite = true)
}
