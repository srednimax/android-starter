package app.starter.ui.items

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import app.starter.R
import app.starter.theme.Spacing
import app.starter.ui.appViewModelExtras
import app.starter.ui.common.DetailScaffold
import coil3.compose.AsyncImage

@Composable
fun ItemDetailScreen(
    itemId: String,
    onEdit: () -> Unit,
    onBack: () -> Unit,
    onDeleted: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ItemDetailViewModel =
        viewModel(factory = ItemDetailViewModel.factoryFor(itemId), extras = appViewModelExtras()),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    // A row can vanish underneath this screen — deleted here, or restored over by a backup. Leaving
    // rather than rendering an empty detail screen is the honest response, and it is a
    // `LaunchedEffect` rather than an `if` in the body because navigating during composition is a
    // side effect and Compose will run the body more than once.
    LaunchedEffect(state.gone) {
        if (state.gone) onDeleted()
    }

    val item = state.item
    DetailScaffold(
        title = item?.title ?: stringResource(R.string.item_detail_title),
        onBack = onBack,
        modifier = modifier,
        actions = {
            IconButton(onClick = onEdit) {
                Icon(Icons.Filled.Edit, contentDescription = stringResource(R.string.action_edit))
            }
            IconButton(onClick = viewModel::delete) {
                Icon(Icons.Filled.Delete, contentDescription = stringResource(R.string.action_delete))
            }
        },
    ) { contentModifier ->
        if (item != null) {
            Column(
                modifier = contentModifier.verticalScroll(rememberScrollState()).padding(Spacing.base),
            ) {
                item.imagePath?.let { path ->
                    // Coil renders a missing file as its error painter rather than throwing, which
                    // is the "missing media is a placeholder, never a crash" house rule for free. A
                    // restored backup may legitimately lack the image files.
                    AsyncImage(
                        model = viewModel.resolve(path),
                        contentDescription = null,
                        modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.base),
                    )
                }
                item.notes?.takeIf(String::isNotBlank)?.let { notes ->
                    Text(notes, style = MaterialTheme.typography.bodyLarge)
                }
            }
        }
    }
}
