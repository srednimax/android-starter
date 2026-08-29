package app.starter.data

import androidx.room.migration.Migration

/**
 * Every migration this build can run, in the order they were written.
 *
 * **Registering it here is the half that is easy to forget**, and forgetting it fails silently: the
 * migration compiles, its test passes (a test opens the database directly), and Room simply never
 * runs it on a real upgrade. `scripts/schema-gate.py` checks this array for exactly that reason.
 *
 * Kotlin note: `arrayOf()` rather than `listOf()` because Room's `addMigrations` takes a vararg,
 * and `*APP_MIGRATIONS` spreads an array into one. `SchemaGate` converts it to a list of integer
 * pairs so the reachability rule can be a pure function.
 */
val APP_MIGRATIONS: Array<Migration> = arrayOf()

/*
 * ---------------------------------------------------------------------------------------------
 * Writing the next one
 * ---------------------------------------------------------------------------------------------
 *
 *     val MIGRATION_1_2 =
 *         object : Migration(1, 2) {
 *             override fun migrate(db: SupportSQLiteDatabase) {
 *                 db.execSQL("ALTER TABLE `items` ADD COLUMN `favourite` INTEGER NOT NULL DEFAULT 0")
 *             }
 *         }
 *
 * **Transcribe the SQL from `schemas/<n>.json`, do not paraphrase the entities.** Room compares the
 * migrated database against that JSON and fails on any difference — a missing index, a column
 * declared TEXT where the entity says INTEGER, a foreign key with a different ON DELETE. Copy the
 * `createSql` out of the exported schema; typing it from the Kotlin is how you get a migration that
 * passes review and fails on a device.
 *
 * The two that are cheap
 * ----------------------
 * CREATE TABLE and ALTER TABLE … ADD COLUMN touch nothing that already exists. No existing row is
 * read or rewritten, so no user's data is at risk. Most migrations are one of these.
 *
 * The one that is not
 * -------------------
 * **SQLite at minSdk 26 has no ALTER TABLE … DROP COLUMN.** Removing or retyping a column means
 * rebuilding the table: create the new shape under a temporary name, INSERT INTO … SELECT the rows
 * across, DROP the original, ALTER TABLE … RENAME. Three things go wrong there, and all three have
 * shipped in real apps:
 *
 *   - **The DROP cascades.** Any table with a foreign key onto the one being rebuilt loses its rows
 *     when the parent is dropped, and `runMigrationsAndValidate` compares *shapes* — it cannot see
 *     that a child table is now empty. Stage those rows into a temporary table and put them back,
 *     and have the test count **rows**, not columns.
 *   - **PRAGMA foreign_keys is off inside a Room migration** and on outside it, so the behaviour you
 *     test by hand in a SQLite client is not the behaviour you get.
 *   - **Indices are not carried across a rename.** Re-create every one the schema JSON lists.
 *
 * Batch a phase's changes into one version
 * ----------------------------------------
 * If three features landing this month all change the schema, one migration that does all three
 * beats three that each prove a shape no shipped build ever held. The version climbs when you
 * release, not when you commit.
 */
