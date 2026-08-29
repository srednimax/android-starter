package app.starter.theme

import android.os.Build
import androidx.activity.compose.LocalActivity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import app.starter.data.ThemeMode

/**
 * The app's theme.
 *
 * [dynamicColor] defaults to **false** per ADR-0006: the app owns its palette and Material You is
 * opt-in. This is not a style preference. With dynamic colour on, nothing on Android 12+ reads
 * [LightColors] or [DarkColors] at all — so the brand you generated in `Color.kt` would be
 * invisible on almost every device that runs the app. It is only visible because this defaults off.
 *
 * A Settings toggle that lets a user turn Material You back on passes `true` here.
 *
 * [themeMode] is the other Settings lever. It decides which of the two schemes applies; the window
 * background and the system-bar scrim are outside Compose's reach and are moved by [applyThemeMode]
 * instead. Resolved here rather than read back from the configuration so the scheme is right on the
 * *first* composition — AppCompat's `onConfigurationChanged` arrives a beat later, and one frame in
 * the wrong palette is what this whole setting exists to stop.
 */
@Composable
fun AppTheme(
    themeMode: ThemeMode = ThemeMode.SYSTEM,
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit,
) {
    val darkTheme =
        when (themeMode) {
            ThemeMode.SYSTEM -> isSystemInDarkTheme()
            ThemeMode.LIGHT -> false
            ThemeMode.DARK -> true
        }

    val colorScheme =
        when {
            // Wallpaper-derived schemes exist only on Android 12+; below that the opt-in silently
            // has nothing to opt into, and the app's own palette applies.
            dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
                val context = LocalContext.current
                if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
            }
            darkTheme -> DarkColors
            else -> LightColors
        }

    SystemBarAppearance(darkTheme)

    MaterialTheme(colorScheme = colorScheme, typography = Typography, content = content)
}

/**
 * Dark icons on the status and navigation bars under a light scheme, light icons under a dark one.
 *
 * **This is the runtime half of the edge-to-edge window**, and it lives here rather than in
 * `themes.xml` because the answer follows the app's own palette rather than the system's, and a
 * theme attribute is fixed at inflation. The other half — the scrim behind the bars — is static and
 * does live in the theme; `values/colors.xml` explains why both halves exist at all.
 *
 * Kotlin/Compose note: `DisposableEffect` is the "run this side effect and clean up after it" hook
 * — the closest analogue is `useEffect` with a cleanup return. Its keys are the dependency array:
 * the body re-runs when any of them changes and not otherwise, so flipping the phone into dark mode
 * repaints the icons while an ordinary recomposition does not touch the window at all. Nothing is
 * owed on the way out — the window is the activity's and outlives this composition — so `onDispose`
 * is empty rather than absent, which the API requires.
 *
 * `LocalActivity` is null in a `@Preview`, where there is no window to write to; returning early is
 * what keeps the previews rendering.
 */
@Composable
private fun SystemBarAppearance(darkTheme: Boolean) {
    val activity = LocalActivity.current ?: return
    val view = LocalView.current
    DisposableEffect(activity, view, darkTheme) {
        WindowCompat.getInsetsController(activity.window, view).apply {
            isAppearanceLightStatusBars = !darkTheme
            isAppearanceLightNavigationBars = !darkTheme
        }
        onDispose {}
    }
}
