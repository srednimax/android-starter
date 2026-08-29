package app.starter.data.backup

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * The manifest is what makes "refuse politely" possible, so its round trip is worth pinning.
 *
 * The forward-compatibility case is the one that matters: a **newer** archive carries fields this
 * build has never heard of, and it still has to parse far enough for the schema check to reject it
 * with a sentence instead of an exception.
 */
class BackupManifestTest {
    @Test
    fun `a manifest survives a round trip`() {
        val manifest = BackupManifest(schemaVersion = 3, createdAt = 1_700_000_000_000, appVersion = "1.2.0")
        val decoded = backupJson.decodeFromString<BackupManifest>(backupJson.encodeToString(manifest))
        assertEquals(manifest, decoded)
    }

    @Test
    fun `an archive from a newer build still parses, so it can be refused rather than crash`() {
        val fromTheFuture =
            """{"schemaVersion":99,"createdAt":1,"appVersion":"9.9.9","somethingNew":{"a":1}}"""
        val decoded = backupJson.decodeFromString<BackupManifest>(fromTheFuture)
        assertEquals(99, decoded.schemaVersion)
    }

    @Test
    fun `a field added later has a default, so an old archive still reads`() {
        val old = """{"schemaVersion":1,"createdAt":1}"""
        assertEquals("", backupJson.decodeFromString<BackupManifest>(old).appVersion)
    }
}
