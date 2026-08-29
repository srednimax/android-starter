package app.starter.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import app.starter.BuildConfig

/**
 * The schema version this build expects.
 *
 * The wipe guard reads the *file's* version out of the SQLite header before Room opens it and
 * compares it against this (see `DatabasePreserve.kt`), so the two must stay in step — which is why
 * it is one constant used in both places.
 *
 * `scripts/schema-gate.py` refuses to let a branch merge that bumps this without the matching
 * migration, its registration in [APP_MIGRATIONS], the exported `schemas/<n>.json`, and the
 * `SchemaGateTest` assertion. See ADR-0001.
 */
const val APP_SCHEMA_VERSION = 1

/** The database file name, under the app's standard databases directory. */
const val APP_DATABASE_FILE = "app.db"

/**
 * **An update never loses a user's data** (ADR-0001).
 *
 * While a model is still unsettled — before anything is installed from a store — a schema change is
 * allowed to destroy the database rather than carry a migration for every field added to a shape
 * that is still moving. That is what the destructive fallback below is for, and it is **debug-only**
 * and never silent: the guard in `MainApplication` copies the file aside and asks for consent first.
 *
 * From the first public release, every schema version that reaches a device carries a tested forward
 * migration, and the fallback is gone from the release build entirely.
 *
 * ## The four things a schema bump owes
 *
 * 1. `MIGRATION_x_y` written in `Migrations.kt` **and registered in [APP_MIGRATIONS]** — an
 *    unregistered migration is one Room will never run, and the build is otherwise perfectly happy.
 * 2. The exported `app/schemas/<AppDatabase>/<n>.json`, committed.
 * 3. A `SchemaGateTest` assertion that the launch gate lets the upgrade through.
 * 4. A migration test that reads **rows back** after migrating, rather than asserting nothing threw.
 *
 * `scripts/schema-gate.py` enforces 1–3 mechanically in CI. The fourth is yours.
 *
 * ⚠️ **Every migration test opens the database directly and so walks past the launch gate.** A green
 * migration suite therefore says nothing about whether the gate lets a real upgrade through — that
 * is a separate assertion, and it is how an app can ship a refusal screen to every existing install
 * with a fully green test run behind it. Verify an upgrade on a phone, not only in a test.
 */
@Database(
    entities = [ItemEntity::class],
    version = APP_SCHEMA_VERSION,
    // Room writes the schema JSON these migrations are transcribed from. Committed, and shipped
    // inside the androidTest APK so MigrationTestHelper can read them on the device.
    exportSchema = true,
)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun itemDao(): ItemDao
}

/**
 * Whether this build may let Room empty the database instead of migrating it.
 *
 * A build takes migrations **or** the destructive fallback, never both — which is why the launch
 * gate asks this question *before* it asks whether a migration path exists. A debug build with the
 * fallback on has no migration registered to walk, so a path that exists on paper is not one this
 * build can take, and treating it as if it could would let Room empty the file with no consent
 * screen in front of it.
 */
fun destructiveMigrationAllowed(): Boolean = BuildConfig.DEBUG

/**
 * Builds the database.
 *
 * **Nothing may call this before the launch gate has decided** (ADR-0001). `MainApplication` holds
 * the only reference behind a `lazy` that is forced after the gate passes; that structure *is* the
 * guard, and it is the reason no repository, worker or ViewModel constructs a database of its own.
 *
 * `fallbackToDestructiveMigration(dropAllTables = true)` is applied only when
 * [destructiveMigrationAllowed] — an explicit `if` rather than a conditional argument, because the
 * two builds genuinely take different paths and reading it as one expression hides that.
 */
fun buildAppDatabase(context: Context): AppDatabase =
    Room
        .databaseBuilder(context, AppDatabase::class.java, APP_DATABASE_FILE)
        .apply {
            if (destructiveMigrationAllowed()) {
                fallbackToDestructiveMigration(dropAllTables = true)
            } else {
                addMigrations(*APP_MIGRATIONS)
            }
        }.build()
