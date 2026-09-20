package app.starter.ui.common

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
 * **A live read that went wrong, said as what the user has lost, with one button to the fix.**
 *
 * The idiom for a permission or a system setting the app **can re-read**: it appears only while the
 * state is actually wrong and clears itself on the resume after the user comes back, because it is
 * re-read rather than remembered. `PLAN.md` rule 4's third clause is what it exists to satisfy —
 * these denials fail silently, the app knows and the user does not.
 *
 * It is deliberately *not* the idiom for a grant the app **cannot** read back, such as a vendor's
 * autostart toggle (`work/Autostart.kt`). Those get a permanent row that makes no claim: a banner
 * that could never clear would be the app asserting a state it has no way to observe.
 *
 * The body says what is lost, not what is switched off — "reminders will not arrive" rather than
 * "notifications are disabled", which the user can already see on the screen they are being sent to.
 */
@Composable
fun WarningBanner(
    title: String,
    body: String,
    actionLabel: String,
    onAct: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        color = MaterialTheme.colorScheme.errorContainer,
        contentColor = MaterialTheme.colorScheme.onErrorContainer,
        shape = MaterialTheme.shapes.medium,
        modifier =
            modifier
                .fillMaxWidth()
                .padding(start = Spacing.base, end = Spacing.base, top = Spacing.base),
    ) {
        Column(modifier = Modifier.padding(Spacing.base)) {
            Text(text = title, style = MaterialTheme.typography.titleMedium)
            Text(
                text = body,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = Spacing.tight),
            )
            TextButton(onClick = onAct, modifier = Modifier.padding(top = Spacing.tight)) {
                Text(actionLabel)
            }
        }
    }
}

/**
 * A title, a line of supporting text, and a switch — **and the whole row is the target**.
 *
 * A 48dp strip the width of the screen is far easier to hit than a 32dp control at the edge of it,
 * which is why this is a `Row` with a `clickable` on it rather than a `Switch` with a label beside
 * it. It lived privately inside Settings while Settings was the only caller; it is here because the
 * second caller is how the padding drifts (see [DetailScaffold]).
 *
 * **`enabled = false` draws the row inert rather than hiding it**, which is the part worth keeping.
 * A control the app cannot honour on this particular phone — a feature the ROM refuses, a toggle
 * that needs hardware this device lacks — leaves the user unable to tell the app from an app that
 * behaves differently on their phone than on someone else's. It disables the row's own `clickable`
 * as well as the switch: a row that still took taps and did nothing would be worse than one that
 * says no.
 */
@Composable
fun SwitchRow(
    title: String,
    subtitle: String,
    checked: Boolean,
    onChange: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    Row(
        modifier =
            modifier
                .fillMaxWidth()
                .clickable(enabled = enabled) { onChange(!checked) }
                .padding(horizontal = Spacing.base, vertical = Spacing.snug),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyLarge)
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Switch(checked = checked, onCheckedChange = onChange, enabled = enabled)
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
