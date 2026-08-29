package app.starter.data

import androidx.room.testing.MigrationTestHelper
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * **The template for every migration test you will write.**
 *
 * At schema 1 there is nothing to migrate, so this file only proves the *harness* works — that the
 * exported schema JSON is readable on the device and `MigrationTestHelper` can build a database from
 * it. That is worth having on day one, because the day you need it is the day you are also debugging
 * a migration.
 *
 * ## Writing the real one
 *
 * ```kotlin
 * @Test
 * fun migrate1To2() {
 *     helper.createDatabase(TEST_DB, 1).apply {
 *         execSQL("INSERT INTO items (id, title, createdAt) VALUES ('a', 'kept', 1)")
 *         close()
 *     }
 *     val db = helper.runMigrationsAndValidate(TEST_DB, 2, true, MIGRATION_1_2)
 *     db.query("SELECT title FROM items WHERE id = 'a'").use {
 *         assertTrue(it.moveToFirst())
 *         assertEquals("kept", it.getString(0))   // ← rows, not shapes
 *     }
 * }
 * ```
 *
 * **Read rows back. Do not just assert that nothing threw.** `runMigrationsAndValidate` compares the
 * migrated database's *shape* against the exported JSON — it is completely blind to a table whose
 * rows were emptied by a cascading `DROP`. A migration that destroys every row and rebuilds the
 * schema correctly passes a shape check with flying colours.
 *
 * ⚠️ **This test opens the database directly and so walks straight past the launch gate.** Nothing
 * in this file says anything about whether a real user's upgrade is let through — that is
 * `SchemaGateTest`, and it is a separate claim. Verify an upgrade on a phone too.
 */
@RunWith(AndroidJUnit4::class)
class MigrationTest {
    @get:Rule
    val helper =
        MigrationTestHelper(
            InstrumentationRegistry.getInstrumentation(),
            AppDatabase::class.java,
        )

    @Test
    fun theExportedSchemaIsReadableOnTheDevice() {
        // If this fails, it is almost always the assets wiring in app/build.gradle.kts:
        // `variant.androidTest?.sources?.assets?.addStaticSourceDirectory("$projectDir/schemas")`.
        // Room's exported JSON has to be *inside the test APK*, not merely committed to the repo.
        helper.createDatabase(TEST_DB, 1).close()
    }

    private companion object {
        const val TEST_DB = "migration-test.db"
    }
}
