package app.starter.data

import app.starter.media.MediaFiles
import kotlinx.coroutines.flow.Flow

/**
 * The one place screens talk to for items.
 *
 * **What a repository is for here**, since at this size it looks like a pointless wrapper around the
 * DAO: it is where the *invariants that span more than one store* live. Deleting an item has to
 * delete its image file as well as its row, and neither Room nor the filesystem knows about the
 * other. Put that in a ViewModel and it is one screen's behaviour; put it here and it is the app's.
 *
 * Reads pass straight through, deliberately. A repository that re-wraps every flow in a mapping
 * nobody needs is a layer for its own sake.
 */
class ItemRepository(
    private val dao: ItemDao,
    private val media: MediaFiles,
) {
    fun observeAll(): Flow<List<ItemEntity>> = dao.observeAll()

    fun observeById(id: String): Flow<ItemEntity?> = dao.observeById(id)

    suspend fun all(): List<ItemEntity> = dao.all()

    suspend fun count(): Int = dao.count()

    suspend fun save(item: ItemEntity) = dao.insert(item)

    /**
     * Deletes the row **and** the image behind it.
     *
     * Row first would leave an orphaned file if the process died between the two; file first would
     * leave a row pointing at nothing. Neither is free, so pick the one whose failure the app
     * already handles: a missing image renders as a placeholder (that is a house rule), while an
     * orphaned file is invisible and accumulates forever. So the row goes last.
     */
    suspend fun delete(item: ItemEntity) {
        item.imagePath?.let(media::delete)
        dao.delete(item)
    }
}
