package app.starter.work

import android.content.BroadcastReceiver
import android.content.Context
import app.starter.data.APP_DATABASE_FILE
import app.starter.data.APP_SCHEMA_VERSION
import app.starter.data.SchemaGate
import app.starter.data.readUserVersion
import app.starter.data.schemaGateDecision
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * **The wipe guard, asked from a background entry point** — the one shape every worker and every
 * receiver in this package needs before it touches anything (ADR-0001).
 *
 * The hazard is specific: the OS can start this process to run a worker or deliver a broadcast with
 * no UI and no user present, and anything that forces the container over a schema this build cannot
 * open destroys the database in the background on a phone nobody is looking at. So the question is
 * asked out of four bytes of the file header rather than by opening anything, and the answer is
 * `true` exactly when the right move is to do nothing.
 *
 * **It asks the launch gate's question, not "do the versions differ".** A debug build still blocks
 * on any mismatch — it has no migrations registered, so opening means wiping — and a release build
 * still blocks on a file no migration covers, where opening would throw in a process with nobody to
 * show it to. What it does *not* block is the ordinary upgrade: a mismatch a registered migration
 * can walk is one the next database open performs anyway, so a worker that skipped it would be
 * sitting out a migration happening around it. Getting this distinction wrong is what leaves the
 * first reminder after an update unposted, and the chain stopped until someone opens the app.
 *
 * One function rather than the same three lines in five places. `schemaGateDecision` is the pure
 * predicate underneath and is tested as a truth table; this is only the file read in front of it.
 */
internal fun Context.schemaBlocksBackgroundWork(): Boolean =
    schemaGateDecision(
        readUserVersion(getDatabasePath(APP_DATABASE_FILE)),
        APP_SCHEMA_VERSION,
    ) != SchemaGate.Open

/**
 * Runs [work] off the main thread while holding the broadcast open, and lets go when it finishes.
 *
 * `onReceive` runs on the **main thread** and the receiver is considered finished the moment it
 * returns — after which the process is a candidate for death. Everything these receivers do is
 * disk-bound, so doing it inline would be a StrictMode violation on the main thread and doing it in
 * a bare thread would race the process teardown. `goAsync()` is the platform's answer to both: it
 * hands back a token that keeps the broadcast alive until `finish()`.
 *
 * Kotlin note: `CoroutineScope(Dispatchers.IO).launch` is a fire-and-forget background job — the
 * closest thing to an un-awaited `async` call in JS. There is no lifecycle to scope it to here (a
 * receiver has none), which is exactly why the `finish()` in `finally` is not optional: it is what
 * tells Android the work is over, and skipping it on a throw would hold the process open for the
 * ten seconds Android allows before killing it anyway.
 */
internal fun BroadcastReceiver.rebuildInBackground(
    context: Context,
    work: suspend (Context) -> Unit,
) {
    val pending = goAsync()
    // The receiver's own Context is short-lived; the application one outlives the broadcast.
    val appContext = context.applicationContext
    CoroutineScope(Dispatchers.IO).launch {
        try {
            work(appContext)
        } finally {
            pending.finish()
        }
    }
}
