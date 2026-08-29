package app.starter.ui.support

import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.viewmodel.compose.viewModel
import app.starter.R
import app.starter.theme.Spacing
import app.starter.ui.appViewModelExtras
import app.starter.ui.common.DetailScaffold

/**
 * One licence's full text, read out of `assets/licences/<spdx-id>.txt`.
 *
 * **The text ships with the binary rather than being linked.** Apache-2.0 §4(a) requires a copy of
 * the licence to travel with the distribution; a URL is not a copy, and it stops working the day the
 * host reorganises. The build fails if a dependency's licence is not on the allowlist, which is what
 * stops a new dependency arriving with no text behind it.
 */
@Composable
fun LicenceTextScreen(
    spdxId: String,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: LicencesViewModel =
        viewModel(factory = LicencesViewModel.Factory, extras = appViewModelExtras()),
) {
    // `produceState` runs a suspending read and exposes the result as state — roughly a `useEffect`
    // that sets state when it resolves. Keyed on the id, so navigating to a different licence
    // re-reads rather than showing the previous one.
    val text by produceState(initialValue = null as String?, spdxId) {
        value = viewModel.licenceText(spdxId)
    }

    DetailScaffold(title = spdxId, onBack = onBack, modifier = modifier) { contentModifier ->
        Text(
            text = text ?: stringResource(R.string.licence_text_missing),
            style = MaterialTheme.typography.bodySmall,
            modifier =
                contentModifier
                    .verticalScroll(rememberScrollState())
                    .padding(Spacing.base),
        )
    }
}
