package app.starter.data.backup

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/** The entry inside the archive that says what the archive is. */
const val MANIFEST_ENTRY = "manifest.json"

/** Where the database copy sits inside the archive. */
const val DATABASE_ENTRY = "database/app.db"

/**
 * What a backup says about itself.
 *
 * **A restore reads this first and refuses on a schema it does not understand.** Without a manifest
 * the only way to find out an archive is from a newer version of the app is to open its database and
 * have Room throw — by which point the app has already replaced the live file. The manifest is what
 * makes "refuse politely" possible.
 *
 * Kotlin note: `@Serializable` with defaults is how kotlinx.serialization spells "optional". Give
 * every field added later a default, or a new version of the app cannot read an old archive.
 */
@Serializable
data class BackupManifest(
    /** The `APP_SCHEMA_VERSION` of the build that wrote it. */
    val schemaVersion: Int,
    /** Epoch millis. Shown to the user when they pick a file to restore. */
    val createdAt: Long,
    /** The app's `versionName`, for a human reading a support email. Never acted on. */
    val appVersion: String = "",
)

/**
 * `ignoreUnknownKeys` so a *newer* archive with extra fields still parses far enough for the schema
 * check to reject it with a sentence instead of an exception. `isLenient` is deliberately not set:
 * the input is machine-written, and accepting malformed JSON would only hide a broken writer.
 */
val backupJson: Json =
    Json {
        ignoreUnknownKeys = true
        prettyPrint = true
    }
