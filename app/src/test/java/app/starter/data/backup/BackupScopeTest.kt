package app.starter.data.backup

import app.starter.media.MediaKind
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class BackupScopeTest {
    /**
     * **The one assertion that stops a new media kind from silently never being backed up.**
     *
     * Adding a `MediaKind` and forgetting to put it in a scope is invisible: exports keep working,
     * the new images simply are not in them, and nobody finds out until a restore.
     */
    @Test
    fun `the widest scope covers every media kind`() {
        assertEquals(MediaKind.entries.toSet(), BackupScope.Everything.mediaKinds.toSet())
    }

    @Test
    fun `every scope has a filename-safe slug`() {
        assertTrue(BackupScope.entries.all { it.slug.matches(Regex("[a-z][a-z-]*")) })
    }
}
