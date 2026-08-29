package app.starter.ui.items

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
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

@Composable
fun ItemEditorScreen(
    itemId: String?,
    onDone: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ItemEditorViewModel =
        viewModel(factory = ItemEditorViewModel.factoryFor(itemId), extras = appViewModelExtras()),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    // Leave once the save has landed — not when the button is pressed. The difference matters: the
    // write is asynchronous, and navigating first would cancel the `viewModelScope` coroutine doing
    // it. That is the classic way an editor silently loses the last save.
    LaunchedEffect(state.saved) {
        if (state.saved) onDone()
    }

    // Photo Picker, not a storage permission. It hands back a Uri for one file the user chose, needs
    // no permission at all, and is the only image path Play does not ask questions about.
    val pickImage =
        rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
            if (uri != null) viewModel.setImage(uri)
        }

    DetailScaffold(
        title = stringResource(if (itemId == null) R.string.item_add else R.string.action_edit),
        onBack = onDone,
        modifier = modifier,
    ) { contentModifier ->
        Column(
            modifier = contentModifier.verticalScroll(rememberScrollState()).padding(Spacing.base),
        ) {
            OutlinedTextField(
                value = state.title,
                onValueChange = viewModel::setTitle,
                label = { Text(stringResource(R.string.item_title_label)) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = state.notes,
                onValueChange = viewModel::setNotes,
                label = { Text(stringResource(R.string.item_notes_label)) },
                minLines = 3,
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.snug),
            )
            OutlinedButton(
                onClick = {
                    pickImage.launch(
                        PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly),
                    )
                },
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.snug),
            ) {
                Text(stringResource(R.string.item_pick_image))
            }
            Button(
                onClick = viewModel::save,
                enabled = state.canSave,
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.section),
            ) {
                Text(stringResource(R.string.action_save))
            }
        }
    }
}
