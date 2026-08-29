package app.starter.work

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.LocalActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationManagerCompat

/** How an ask ended. Three outcomes, because the third one needs a different button. */
enum class NotificationPermissionOutcome {
    Granted,

    /** Refused, and askable again — Android permits two denials before it stops showing the dialog. */
    Denied,

    /**
     * Refused for good, or switched off in settings. The system dialog will never appear again, so
     * the only way back is the app's own settings screen.
     */
    PermanentlyDenied,
}

/**
 * **The app's one ask for `POST_NOTIFICATIONS`, and the only caller of a permission request
 * anywhere in it.**
 *
 * One function because Android permits only two denials before the dialog stops appearing, and
 * the arithmetic (ADR-0003) only works if there is a single place spending them. Every host calls *this*, so two of them cannot both fire: they are the
 * same composable in two places rather than two asks that happen to agree.
 *
 * **Permanent refusal is recognised from the result, not guessed at beforehand.**
 * `shouldShowRequestPermissionRationale` is famously ambiguous *before* an ask — it returns false
 * both for "never asked" and for "asked twice and refused" — but after a denial it is exact. So the
 * request is fired and the answer read: denied with a rationale still available is an ordinary no,
 * denied with none left is Android saying it will not ask again, and the caller offers app settings
 * instead of a button that would silently do nothing. The two-denial arithmetic is about not *spending* both; this
 * is the case after they are spent, and it is the one users actually hit.
 *
 * Kotlin note: this returns a lambda rather than performing anything. `rememberLauncherForActivityResult`
 * has to be called during composition — it registers a result callback with the Activity — but the
 * *launch* belongs to a button press, so the composable hands back the trigger. Roughly a React hook
 * returning a stable callback.
 */
@Composable
fun rememberNotificationPermissionAsk(onOutcome: (NotificationPermissionOutcome) -> Unit): () -> Unit {
    val context = LocalContext.current
    val activity = LocalActivity.current

    val launcher =
        rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            onOutcome(
                when {
                    granted -> NotificationPermissionOutcome.Granted
                    activity != null &&
                        ActivityCompat.shouldShowRequestPermissionRationale(
                            activity,
                            Manifest.permission.POST_NOTIFICATIONS,
                        ) -> NotificationPermissionOutcome.Denied
                    else -> NotificationPermissionOutcome.PermanentlyDenied
                },
            )
        }

    return {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            // Below API 33 there is no runtime permission: notifications are granted at install and
            // the only way off is the settings switch, which nothing can re-ask for. So the answer
            // is already known, and "off" is permanent in the only sense that matters — app settings
            // is the sole way back.
            onOutcome(
                if (NotificationManagerCompat.from(context).areNotificationsEnabled()) {
                    NotificationPermissionOutcome.Granted
                } else {
                    NotificationPermissionOutcome.PermanentlyDenied
                },
            )
        } else {
            launcher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}

/**
 * This app's page in Android's settings — where a permanently refused permission can still be turned
 * back on, and the only remaining route once the system dialog is spent.
 */
fun Context.openAppNotificationSettings() {
    startFirstAvailable(
        // The notification page directly, which is where the switch actually is.
        Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
            .putExtra(Settings.EXTRA_APP_PACKAGE, packageName),
        // The app's details page, one tap further away and present on every device.
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", packageName, null)),
    )
}

/**
 * One channel's **own** page in Android's settings — where an importance that has been lowered can
 * be raised back up, which is the only place it can be (9b).
 *
 * A separate way in from [openAppNotificationSettings] rather than a reuse of it, because the fix is
 * a different control: the app-wide switch lives on the app's page, the per-kind level lives on a
 * screen below it, and landing a user one screen above the toggle they need is how a two-tap fix
 * becomes a hunt through a list of four channel names.
 *
 * `ACTION_CHANNEL_NOTIFICATION_SETTINGS` and channels both arrived in API 26, which is `minSdk`, so
 * there is no version branch to write — but a skin can still decline to export it, so it falls
 * through to the same two screens as above.
 */
fun Context.openChannelNotificationSettings(channel: ReminderChannel) {
    startFirstAvailable(
        Intent(Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS)
            .putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
            .putExtra(Settings.EXTRA_CHANNEL_ID, channel.id),
        Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
            .putExtra(Settings.EXTRA_APP_PACKAGE, packageName),
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", packageName, null)),
    )
}

/**
 * Tries each screen in turn and stops at the first one that opens.
 *
 * Every way into system settings this app offers is a *best guess at a screen that may not exist
 * here* — a settings action is not a guaranteed part of the platform, and an OEM may drop one or
 * keep it unexported. So the callers above list their targets most-specific-first — the screen that
 * holds the actual control, then the ones above it — and this walks them until one opens.
 *
 * Kotlin note: `vararg` is the same idea as JS rest parameters, so the call sites read as a list of
 * arguments rather than an explicitly built `listOf`.
 */
private fun Context.startFirstAvailable(vararg intents: Intent) {
    for (intent in intents) {
        try {
            startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            return
        } catch (e: ActivityNotFoundException) {
            // Not on this device — try the next one.
        } catch (e: SecurityException) {
            // Present but not exported to us, which is the same outcome from here.
        }
    }
}
