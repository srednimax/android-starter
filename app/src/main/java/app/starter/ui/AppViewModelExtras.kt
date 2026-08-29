package app.starter.ui

import android.app.Application
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.Companion.APPLICATION_KEY
import androidx.lifecycle.viewmodel.CreationExtras
import androidx.lifecycle.viewmodel.MutableCreationExtras

/**
 * The `CreationExtras` a ViewModel factory needs inside a navigation entry.
 *
 * Nav3 hands every back-stack entry its own `ViewModelStoreOwner` (see `appEntryDecorators` in
 * `Navigation.kt`) — that is what makes a ViewModel die with the screen that owns it. But it is a
 * *bare* owner: unlike an Activity it has no default extras, so `APPLICATION_KEY` is missing, and
 * every factory here reads that key to reach `AppContainer`. Without it `this[APPLICATION_KEY]` is
 * null and the cast in the initializer throws the moment the screen opens.
 *
 * So a screen inside a navigation entry passes this: `viewModel(factory = …, extras = …)`.
 * Composables outside `NavDisplay` resolve to the Activity and need nothing.
 */
@Composable
fun appViewModelExtras(): CreationExtras {
    val application = LocalContext.current.applicationContext as Application
    // Kotlin note: `remember(key)` is useMemo — rebuild only if the application instance changes,
    // which in practice is never, so the extras are allocated once per screen.
    return remember(application) {
        MutableCreationExtras().apply { set(APPLICATION_KEY, application) }
    }
}
