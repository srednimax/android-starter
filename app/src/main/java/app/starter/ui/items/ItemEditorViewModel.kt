package app.starter.ui.items

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.Companion.APPLICATION_KEY
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import app.starter.MainApplication
import app.starter.data.ItemEntity
import app.starter.data.ItemRepository
import app.starter.media.MediaFiles
import app.starter.media.MediaKind
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ItemEditorUiState(
    val title: String = "",
    val notes: String = "",
    val imagePath: String? = null,
    val saving: Boolean = false,
    /** Set once, when the save has landed. The screen watches it and leaves. */
    val saved: Boolean = false,
) {
    /** A title is the one thing an item cannot be without. */
    val canSave: Boolean get() = title.isNotBlank() && !saving
}

class ItemEditorViewModel(
    private val itemId: String?,
    private val repository: ItemRepository,
    private val media: MediaFiles,
) : ViewModel() {
    private val _state = MutableStateFlow(ItemEditorUiState())
    val state: StateFlow<ItemEditorUiState> = _state.asStateFlow()

    private var existing: ItemEntity? = null

    init {
        // Editing: load the row once and seed the form. A `Flow` collected for the lifetime of the
        // editor would be wrong — a change arriving from elsewhere while the user is typing would
        // overwrite what they have half-written.
        if (itemId != null) {
            viewModelScope.launch {
                val item = repository.observeById(itemId).first() ?: return@launch
                existing = item
                _state.update {
                    it.copy(
                        title = item.title,
                        notes = item.notes.orEmpty(),
                        imagePath = item.imagePath,
                    )
                }
            }
        }
    }

    // Kotlin note: `copy()` on a data class is object spread — a new instance with one field
    // changed. `update {}` applies it atomically, which matters because two coroutines can call
    // these at once.
    fun setTitle(value: String) = _state.update { it.copy(title = value) }

    fun setNotes(value: String) = _state.update { it.copy(notes = value) }

    /**
     * Persist a picked image and point the form at it.
     *
     * **Through [MediaFiles], never straight to a file.** It downsamples and re-encodes per kind,
     * bakes in the EXIF rotation and strips the metadata — including the GPS coordinates a camera
     * stamps on every shot, which have no business travelling in a backup.
     */
    fun setImage(source: Uri) {
        viewModelScope.launch {
            val persisted = media.persist(source, MediaKind.Photo)
            // Replace, so the old file does not linger. Best-effort: the record is what matters.
            _state.value.imagePath?.let(media::delete)
            _state.update { it.copy(imagePath = persisted.path) }
        }
    }

    fun save() {
        val snapshot = _state.value
        if (!snapshot.canSave) return
        _state.update { it.copy(saving = true) }
        viewModelScope.launch {
            val item =
                existing?.copy(
                    title = snapshot.title.trim(),
                    notes = snapshot.notes.trim().takeIf(String::isNotBlank),
                    imagePath = snapshot.imagePath,
                ) ?: ItemEntity(
                    title = snapshot.title.trim(),
                    notes = snapshot.notes.trim().takeIf(String::isNotBlank),
                    imagePath = snapshot.imagePath,
                )
            repository.save(item)
            _state.update { it.copy(saving = false, saved = true) }
        }
    }

    companion object {
        fun factoryFor(itemId: String?): ViewModelProvider.Factory =
            viewModelFactory {
                initializer {
                    val app = this[APPLICATION_KEY] as MainApplication
                    ItemEditorViewModel(itemId, app.container.items, app.container.media)
                }
            }
    }
}
