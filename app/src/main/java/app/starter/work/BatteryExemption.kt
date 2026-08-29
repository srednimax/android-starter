package app.starter.work

import android.content.ActivityNotFoundException
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.PowerManager
import android.provider.Settings

/**
 * Xiaomi's autostart manager. The activity that decides, on HyperOS, whether this app's background
 * work is allowed to run at all — and the one with no readable state anywhere (ADR-0003). Named explicitly in the manifest's `<queries>` so it can be looked up at all.
 */
private const val MIUI_SECURITY_CENTER = "com.miui.securitycenter"
private const val MIUI_AUTOSTART_ACTIVITY = "com.miui.permcenter.autostart.AutoStartManagementActivity"

/**
 * Whether Android currently exempts this app from battery optimisation.
 *
 * **Readable without any permission**, which is the whole reason the honest state can lean on it.
 * `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` — the permission that would let the app pop its own
 * grant dialog — is deliberately **not declared**: Play restricts it to apps whose core function is
 * the exemption itself. So the app reads the
 * state, explains it, and opens the screen where the user decides.
 *
 * Spelled the British way like the rest of this codebase; the platform's own American spelling stays
 * where the platform put it. Pick one and be consistent — a codebase with both is a codebase where
 * every call site is a guess.
 */
fun Context.isIgnoringBatteryOptimisations(): Boolean {
    val power = getSystemService(PowerManager::class.java) ?: return false
    return power.isIgnoringBatteryOptimizations(packageName)
}

/**
 * Opens Android's battery-optimisation list, where the user can exempt this app themselves.
 *
 * The app-specific action (`ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`) is the one that needs the
 * restricted permission, so this is its unrestricted sibling: the whole list, with the user one
 * search away from us. Best-effort in the same shape as `openSystemBackupSettings`, and for the same
 * reason — a dead button costs the user more than one extra tap does.
 *
 * @return whether anything opened, so the caller can say so rather than guess.
 */
fun Context.openBatteryOptimisationSettings(): Boolean {
    val actions =
        listOf(
            Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS,
            // Every device has this, and every Settings app of this era opens on a search field.
            Settings.ACTION_SETTINGS,
        )
    for (action in actions) {
        // NEW_TASK, so Settings opens as its own task rather than being pushed onto this app's —
        // without it the user cannot bring the app forward again while they are in there.
        if (startActivitySafely(Intent(action).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))) return true
    }
    return false
}

/**
 * Whether this phone has Xiaomi's autostart screen at all.
 *
 * Answerable only because the manifest declares the package in `<queries>`; without that,
 * package-visibility filtering on API 30+ returns null for an activity that would have launched
 * perfectly well.
 */
fun Context.hasAutostartSettings(): Boolean = autostartIntent().resolveActivity(packageManager) != null

/**
 * Opens Xiaomi's autostart manager, and that is the end of the app's involvement.
 *
 * **Offered once and claimed never** (ADR-0003's amendment). Launching this returns no result and
 * the setting has no public state, so the app cannot know afterwards what the user did — and a
 * checkbox asking them to confirm would have the app repeating the user's guess back to them as its
 * own assurance, which is this ADR's central hazard sourced from a new place. What stands behind the
 * claim instead is 4g's overnight-Doze run on the real device.
 */
fun Context.openAutostartSettings(): Boolean =
    startActivitySafely(autostartIntent().addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))

private fun autostartIntent(): Intent =
    Intent().setComponent(ComponentName(MIUI_SECURITY_CENTER, MIUI_AUTOSTART_ACTIVITY))

/**
 * `startActivity`, reporting failure rather than taking the app down with it.
 *
 * An OEM screen that is present but not exported to us throws `SecurityException`, which is the same
 * outcome from here as it not being there at all.
 *
 * `internal` rather than private since 5a: [openExactAlarmSettings] walks the same fallback list for
 * the same reason, and two copies of a three-line try/catch is how one of them quietly stops
 * catching something.
 */
internal fun Context.startActivitySafely(intent: Intent): Boolean =
    try {
        startActivity(intent)
        true
    } catch (e: ActivityNotFoundException) {
        false
    } catch (e: SecurityException) {
        false
    }
