package app.starter.work

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import androidx.annotation.StringRes
import app.starter.R

/**
 * The notification channels this app owns.
 *
 * **A channel is a separate mute, and that is the only reason to have more than one.** Ask of every
 * pair: would a user who silences A be annoyed to discover it also silenced B? If yes, they are two
 * channels. If no, one channel with two kinds of text in it is simpler and easier to live with.
 *
 * **The importance is per entry**, and it has to be — a routine nudge and something time-critical
 * cannot share a level. The direction is what makes the choice permanent: **Android lets the user
 * lower a channel and never lets the app raise one again.** Creating a channel at `IMPORTANCE_LOW`
 * is making the mute decision on their behalf, in the one direction that cannot be undone. Start at
 * `DEFAULT` unless you have a reason.
 *
 * Kotlin note: enum entries carrying constructor arguments make this a small lookup table rather
 * than the bare constants a JS enum gives you — the same shape as `TopLevelDestination`.
 *
 * @param id what Android stores the channel under. **Never change one**: a renamed id is a new
 *   channel, and every user's mute silently reverts to unmuted.
 * @param nameRes the channel's name in the phone's notification settings. `ReminderChannelsTest`
 *   holds the `channel_<id>_name` / `channel_<id>_description` convention these follow.
 * @param importance what the channel is *created* at, and therefore the ceiling the user can lower
 *   from. Never read it back to make a decision — read the live value from the system instead.
 */
enum class ReminderChannel(
    val id: String,
    @param:StringRes val nameRes: Int,
    @param:StringRes val descriptionRes: Int,
    val importance: Int,
) {
    Reminders(
        "reminders",
        R.string.channel_reminders_name,
        R.string.channel_reminders_description,
        NotificationManager.IMPORTANCE_DEFAULT,
    ),
}

/**
 * Creates every channel, idempotently.
 *
 * `createNotificationChannel` on an id that already exists updates the name and description and
 * leaves the user's importance and their mute alone — which is exactly right, and is why calling
 * this on every launch is safe rather than merely harmless. It is also what makes a channel's name
 * follow an in-app language change.
 */
fun Context.ensureReminderChannels() {
    val manager = getSystemService(NotificationManager::class.java) ?: return
    for (channel in ReminderChannel.entries) {
        manager.createNotificationChannel(
            NotificationChannel(channel.id, getString(channel.nameRes), channel.importance).apply {
                description = getString(channel.descriptionRes)
            },
        )
    }
}
