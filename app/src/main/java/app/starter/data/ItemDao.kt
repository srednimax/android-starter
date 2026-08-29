package app.starter.data

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

/**
 * **Reads return `Flow`; writes are `suspend`.** Screens collect the flow and never call a refresh.
 *
 * Kotlin note for a JS background: a `Flow` is closest to an RxJS `Observable` or an async iterator —
 * a stream you subscribe to, not a promise you await once. Room re-runs the query and re-emits
 * whenever any table the query touches changes, so a write anywhere in the app updates every screen
 * showing the affected rows with no wiring between them. That is the whole reason not to hand-roll
 * a `refresh()`: a hand-rolled one is a list of call sites somebody will forget to add to.
 *
 * `suspend` on the writes is closest to `async` — it can wait without blocking the thread, and Room
 * uses that to move the actual disk write off the main thread for you. Calling a `suspend` function
 * requires a coroutine scope, which is why the repository takes one.
 */
@Dao
interface ItemDao {
    @Query("SELECT * FROM items ORDER BY createdAt DESC")
    fun observeAll(): Flow<List<ItemEntity>>

    @Query("SELECT * FROM items WHERE id = :id")
    fun observeById(id: String): Flow<ItemEntity?>

    /**
     * A one-shot read, for code with no UI to update — a backup export, a worker deciding whether
     * anything is due. Deliberately separate from [observeAll] rather than a `.first()` on it: a
     * flow's first emission is a subscription that has to be torn down again, and in a worker that
     * is a lifecycle to get wrong.
     */
    @Query("SELECT * FROM items ORDER BY createdAt DESC")
    suspend fun all(): List<ItemEntity>

    @Query("SELECT COUNT(*) FROM items")
    suspend fun count(): Int

    // REPLACE rather than ABORT so a restore can re-insert a row it already has. With a UUID
    // primary key that only happens when it is genuinely the same row.
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(item: ItemEntity)

    @Update
    suspend fun update(item: ItemEntity)

    @Delete
    suspend fun delete(item: ItemEntity)

    @Query("DELETE FROM items")
    suspend fun deleteAll()
}
