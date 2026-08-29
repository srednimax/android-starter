package app.starter.data.backup

import app.starter.media.MediaKind

/**
 * How much goes in the archive.
 *
 * **Two scopes, because the two have different sizes and different purposes.** The records alone are
 * small enough to mail to yourself; with every photo it can be hundreds of megabytes, which is a
 * different thing to offer and a different thing to restore.
 *
 * The media kinds are a list of [MediaKind] rather than a list of directory strings, so adding a
 * media kind cannot leave it silently out of every backup — the `when` below stops compiling until
 * someone decides which scopes it belongs to.
 */
enum class BackupScope(
    val slug: String,
) {
    /** The database and the small images. Mailable. */
    Records("records"),

    /** Everything, including full-size photos. */
    Everything("everything"),
    ;

    val mediaKinds: List<MediaKind>
        get() =
            when (this) {
                Records -> listOf(MediaKind.Thumbnail)
                Everything -> MediaKind.entries.toList()
            }
}
