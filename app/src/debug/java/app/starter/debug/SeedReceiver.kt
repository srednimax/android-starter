package app.starter.debug

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import app.starter.MainApplication
import app.starter.data.SampleData
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * Seeds the sample data on demand, so a driver script can put the phone into a known state without
 * walking the UI to do it. **Debug source set only** — it does not exist in a release build.
 *
 * ```bash
 * adb shell am broadcast -n <pkg>.debug/app.starter.debug.SeedReceiver -f 0x00000020 --es variant ""
 * ```
 *
 * ## The two things that make this work from `adb`
 *
 * **`-f 0x00000020` is `FLAG_INCLUDE_STOPPED_PACKAGES`.** A package is in the *stopped* state after
 * `pm clear` until something launches it, and a broadcast to a stopped package is dropped in
 * silence — which looks exactly like a receiver that seeded nothing. Without this flag the whole
 * mechanism appears to work and does nothing.
 *
 * **It reports through the broadcast result**, so the caller can fail on what actually happened
 * rather than on a timeout. `am broadcast` prints `result=0` and the result data, so a driver can
 * assert on it. Without a result there is no way to tell "seeded" from "the process died first".
 *
 * ⚠️ On Xiaomi's HyperOS, **an explicit broadcast to a manifest receiver does not start the process
 * at all** unless *autostart* is granted for the app: `pidof` stays empty with `stopped=false`, and
 * the broadcast is simply never delivered. A run against an unknown autostart state proves nothing
 * either way — read it first with `scripts/device-gate.py`.
 */
class SeedReceiver : BroadcastReceiver() {
    override fun onReceive(
        context: Context,
        intent: Intent,
    ) {
        val variant = intent.getStringExtra("variant").orEmpty()
        val pending = goAsync()
        val app = context.applicationContext as MainApplication
        CoroutineScope(Dispatchers.IO).launch {
            try {
                when (variant) {
                    // The plain sample data. **Never edit what this produces** once screenshots
                    // rest on it — add a named variant instead, applied on top. Every scene, every
                    // before/after comparison and every listing screenshot depends on this fixture
                    // being the same fixture it was last week.
                    "" -> SampleData.seed(app.container.items)
                    else -> {
                        pending.setResult(1, "unknown variant: $variant", null)
                        return@launch
                    }
                }
                pending.setResult(0, "seeded", null)
            } catch (e: Throwable) {
                pending.setResult(1, e.toString(), null)
            } finally {
                pending.finish()
            }
        }
    }
}
