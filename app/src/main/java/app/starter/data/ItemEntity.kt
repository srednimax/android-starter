package app.starter.data

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import java.time.Instant
import java.util.UUID

/**
 * The one thing this app keeps a list of.
 *
 * **This is the placeholder domain — replace it.** It exists so every gate in the repository has
 * something real to bite on: a table for the schema gate, a screen for the screenshot driver,
 * strings for the translation gate, an image path for the media pipeline. Rename it to whatever
 * your app is actually about and the rest of the scaffolding keeps working.
 *
 * ## Two conventions worth keeping when you replace it
 *
 * **A `String` UUID primary key, not an autoincrementing `Int`.** A row has to survive being
 * exported to a backup and restored onto a different install, possibly merged with rows that are
 * already there. Two databases both counting from 1 collide on every id; two databases minting
 * UUIDs never do. The cost is a slightly larger index, which at this scale is nothing.
 *
 * **Timestamps as epoch millis, converted at the edge.** `Converters` maps `Instant` to `Long`, so
 * the column sorts and range-queries as a number while the Kotlin side stays a real instant. Storing
 * a formatted date string instead is the classic mistake: it sorts wrong across timezones and
 * cannot be compared without parsing.
 *
 * Kotlin note: `data class` gives you `copy()` — `item.copy(title = "new")` is the object-spread
 * idiom, returning a new instance with one field changed rather than mutating this one. Room needs
 * the class to be constructible from its columns, which is why every property has a default or is
 * in the constructor.
 */
@Entity(
    tableName = "items",
    // Indexed because the list screen orders by it. An index is not free — it is a second structure
    // to write on every insert — so add one for a column a query actually sorts or filters on, and
    // not on principle.
    indices = [Index("createdAt")],
)
data class ItemEntity(
    @PrimaryKey
    val id: String = UUID.randomUUID().toString(),
    val title: String,
    /** Free text. Nullable rather than empty-string-as-absent: the two are genuinely different. */
    val notes: String? = null,
    /**
     * Relative to `filesDir` — `images/<uuid>.jpg` — never absolute.
     *
     * An absolute path changes across installs and breaks every restored backup, and it is the
     * single most common way an offline app loses its own media. `MediaFiles` writes this form and
     * resolves it at read time; nothing else should build one.
     */
    @ColumnInfo(name = "imagePath")
    val imagePath: String? = null,
    val createdAt: Instant = Instant.now(),
)
