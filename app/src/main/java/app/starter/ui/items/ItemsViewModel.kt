package app.starter.ui.items

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.Companion.APPLICATION_KEY
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import app.starter.MainApplication
import app.starter.data.ItemEntity
import app.starter.data.ItemRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn

/**
 * **One immutable data class for the whole screen's state.**
 *
 * Not one `StateFlow` per field. Two flows that must agree — a list and a "loading" flag, say — can
 * emit out of step, and the frame in between is a UI state that should be impossible. One class
 * makes every rendered combination one the type system approved.
 *
 * `loading` starts true and is the reason there is no flicker of the empty state before the first
 * database read lands. That single frame is the most common visible bug in a Room-backed list.
 */
data class ItemsUiState(
    val items: List<ItemEntity> = emptyList(),
    val loading: Boolean = true,
)

class ItemsViewModel(
    repository: ItemRepository,
) : ViewModel() {
    /**
     * Kotlin note: `stateIn` turns a cold `Flow` into a hot `StateFlow` with a current value — the
     * shape a UI needs, since a composition has to render *something* on its first pass.
     *
     * `WhileSubscribed(5_000)` is the important argument: the upstream query stays alive for five
     * seconds after the last collector goes away. That keeps the data warm across a configuration
     * change (a rotation tears down and rebuilds the composition in well under five seconds) while
     * still releasing it when the user actually leaves. `Eagerly` would keep querying forever;
     * `Lazily` would never release.
     */
    val state: StateFlow<ItemsUiState> =
        repository
            .observeAll()
            .map { items -> ItemsUiState(items = items, loading = false) }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), ItemsUiState())

    companion object {
        /**
         * Reaches `AppContainer` through the application, which is the only object a bare
         * `ViewModelStoreOwner` can be given. `appViewModelExtras()` is what supplies it inside a
         * Nav3 entry — without that, `this[APPLICATION_KEY]` is null and this cast throws.
         */
        val Factory: ViewModelProvider.Factory =
            viewModelFactory {
                initializer {
                    val app = this[APPLICATION_KEY] as MainApplication
                    ItemsViewModel(app.container.items)
                }
            }
    }
}
