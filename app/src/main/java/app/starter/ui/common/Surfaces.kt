package app.starter.ui.common

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import app.starter.R
import app.starter.theme.Spacing

/**
 * The shape every detail screen takes: a top bar with a title and a back arrow, and content below.
 *
 * Extracted because three screens had it and the fourth got the padding subtly wrong. A shared
 * scaffold is not about saving lines — it is about the app looking like one app.
 *
 * `onBack` is nullable rather than defaulted to `{}`: a screen with no back arrow and a screen whose
 * back arrow does nothing look identical in a screenshot and are completely different bugs.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DetailScaffold(
    title: String,
    onBack: (() -> Unit)?,
    modifier: Modifier = Modifier,
    actions: @Composable () -> Unit = {},
    content: @Composable (Modifier) -> Unit,
) {
    Scaffold(
        modifier = modifier,
        topBar = {
            TopAppBar(
                title = { Text(title) },
                navigationIcon = {
                    if (onBack != null) {
                        IconButton(onClick = onBack) {
                            Icon(
                                // AutoMirrored so the arrow points the other way in a right-to-left
                                // locale. The manifest declares `supportsRtl`, which makes this the
                                // app's problem rather than the platform's.
                                imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                                contentDescription = stringResource(R.string.action_back),
                            )
                        }
                    }
                },
                actions = { actions() },
            )
        },
    ) { insets ->
        content(Modifier.padding(insets))
    }
}

/**
 * What a list shows when it is empty.
 *
 * **Say what to do, not that there is nothing.** "No items yet" tells the user what they can already
 * see; "Tap + to add your first item" tells them what to do about it.
 */
@Composable
fun EmptyState(
    message: String,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.fillMaxSize().padding(Spacing.block),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = message,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )
    }
}

/**
 * A section heading.
 *
 * The padding here is the rhythm rule from [Spacing]: [Spacing.section] above, [Spacing.tight]
 * below. Equal padding on both sides is the most common spacing mistake in a hand-built UI — it
 * leaves the header floating between two sections, belonging to neither.
 */
@Composable
fun SectionHeader(
    text: String,
    modifier: Modifier = Modifier,
) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleSmall,
        color = MaterialTheme.colorScheme.primary,
        modifier =
            modifier.padding(
                start = Spacing.base,
                end = Spacing.base,
                top = Spacing.section,
                bottom = Spacing.tight,
            ),
    )
}
