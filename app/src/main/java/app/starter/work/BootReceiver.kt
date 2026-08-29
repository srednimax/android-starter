package app.starter.work

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * Puts the daily sweep back after a restart.
 *
 * **No schedule is read from anywhere**: what is due is derived from the data, and the OS schedule
 * was only ever a cache of that derivation. With one sweep there is nothing per-reminder to rebuild,
 * which is why the "re-enqueued on boot, fires again, notifies twice" failure that per-reminder work
 * invites cannot happen here.
 *
 * WorkManager normally restores its own enqueued work across a reboot, so this is a belt-and-braces
 * [ensureSweepEnqueued] rather than a full reschedule. **AlarmManager restores nothing**, so if you
 * add exact alarms they need a real reschedule here, not an ensure (ADR-0003).
 *
 * On Xiaomi's HyperOS this receiver runs only if *autostart* is granted for the app — off by
 * default, and not something the app can read. With it denied, process start is the only rebuild
 * left. See `scripts/device-gate.py`.
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(
        context: Context,
        intent: Intent,
    ) {
        // The manifest filters for this already; the check is what stops a re-used receiver acting
        // on a broadcast it was never registered for.
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        rebuildInBackground(context) { ensureSweepEnqueued(it) }
    }
}
