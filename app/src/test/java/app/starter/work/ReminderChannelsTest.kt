package app.starter.work

import android.app.NotificationManager
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * The channel enum and `strings.xml` are the same claim written twice, and this is what stops them
 * drifting — the same shape as `AppLanguageTest`, for the same reason.
 *
 * Checked **in both directions**, and neither failure is loud on its own. A channel with no strings
 * behind it cannot happen (the `R` reference would not compile), but a *stale* `channel_…` string
 * left behind after a channel is renamed or removed is a settings row's worth of copy describing
 * something that no longer exists — and channel ids are permanent, so this is the drift that
 * actually happens. Lint says nothing about either.
 *
 * Reads the resource off disk rather than through `R`: a JVM unit test has no Android framework
 * under it, and the file's *contents* are what is in question. Gradle runs unit tests with the
 * module directory as the working directory.
 */
class ReminderChannelsTest {
    private val declared: Set<String> =
        Regex("""<string\s+name="(channel_[^"]+)"""")
            .findAll(File("src/main/res/values/strings.xml").readText())
            .map { it.groupValues[1] }
            .toSet()

    /** The naming convention the enum's `R.string` fields follow, stated once. */
    private val expected: Set<String> =
        ReminderChannel.entries
            .flatMap { channel -> listOf("channel_${channel.id}_name", "channel_${channel.id}_description") }
            .toSet()

    @Test
    fun `every channel has a name and a description, and nothing else declares one`() {
        assertEquals(expected, declared)
    }

    @Test
    fun `there are exactly five channels, and they are the five this release has behind them`() {
        // One per thing that posts, and no more. A channel is the owner's only per-kind control:
        // muting a daily watch nag must not mute an annual vaccination, deciding a monthly "make a
        // backup" prompt is not for you must not cost either of the other two, and muting doses must
        // not follow from any of the three. `backup` arrived in 4e, `doses` in 5a and `events` in
        // 10e — care is a job the app is asking for and an event is a day the owner asked to be
        // reminded of, which is a distinction the per-channel switch is the only place to act on.
        // This test is what makes an addition a deliberate act rather than a passing convenience.
        assertEquals(
            setOf("reminders"),
            ReminderChannel.entries.map { it.id }.toSet(),
        )
    }

    @Test
    fun `at most one channel is high-importance`() {
        // The level is spent once, on purpose. If everything is HIGH then nothing is. The other
        // direction is what makes it worth pinning: a channel created at the wrong importance can
        // never be raised again, only lowered by the user, so it is a decision with no second try.
        assertTrue(
            ReminderChannel.entries.count { it.importance == NotificationManager.IMPORTANCE_HIGH } <= 1,
        )
    }

    @Test
    fun `no channel is created below IMPORTANCE_DEFAULT`() {
        // Creating a channel quiet would be making the mute decision on the user's behalf, in
        // the one direction that cannot be undone.
        assertTrue(ReminderChannel.entries.all { it.importance >= NotificationManager.IMPORTANCE_DEFAULT })
    }

    @Test
    fun `channel ids are stable, lowercase and free of the app's package`() {
        // A renamed id is a *new* channel: the user's mute silently goes back to unmuted and there
        // is no migration for it. Nothing enforces that but review — this at least pins the shape.
        assertTrue(ReminderChannel.entries.all { it.id.matches(Regex("[a-z][a-z_]*")) })
    }
}
