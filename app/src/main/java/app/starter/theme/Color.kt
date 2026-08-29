package app.starter.theme

import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color

// GENERATED — do not hand-edit individual roles.
//
// Both schemes are derived from four brand seeds by Material's tonal palette
// construction (CAM16/HCT): the seeds are the judgement, the ~36 roles are
// arithmetic. Hand-picking a role breaks the fixed tonal relationship it holds
// with the rest of its family, and the failure shows up as a contrast bug on one
// screen out of thirty rather than as a visible mistake here.
//
//   primary   #4C6FA5  — brand: filled buttons, FAB, selected tab
//   secondary #6B7A8F  — quiet containers: chips, tonal buttons, selected segment
//   tertiary  #9A6BA5  — accents and caution markers, used sparingly
//   neutral   #DCDFE4  — seeds every surface, so it decides warm or cool overall
//
// Error stays M3 baseline (hue 25, chroma 84): a safety signal, not a brand choice.
//
// To change the palette, edit the seeds in scripts/gen_scheme.py and re-run it.
// Colours come from MaterialTheme, never literals, and dynamic colour defaults
// off (ADR-0006) so this file is what a user actually sees.

private val AppLightColors =
    lightColorScheme(
        primary = Color(0xFF3B5F94),
        onPrimary = Color(0xFFFFFFFF),
        primaryContainer = Color(0xFFD4E3FF),
        onPrimaryContainer = Color(0xFF001B3E),
        inversePrimary = Color(0xFFA6C8FF),
        secondary = Color(0xFF515F73),
        onSecondary = Color(0xFFFFFFFF),
        secondaryContainer = Color(0xFFD4E3FB),
        onSecondaryContainer = Color(0xFF0D1C2E),
        tertiary = Color(0xFF7A4E85),
        onTertiary = Color(0xFFFFFFFF),
        tertiaryContainer = Color(0xFFFDD6FF),
        onTertiaryContainer = Color(0xFF30073D),
        error = Color(0xFFBA1B1B),
        onError = Color(0xFFFFFFFF),
        errorContainer = Color(0xFFFFDAD4),
        onErrorContainer = Color(0xFF410001),
        background = Color(0xFFF6F9FE),
        onBackground = Color(0xFF181C20),
        surface = Color(0xFFF6F9FE),
        onSurface = Color(0xFF181C20),
        surfaceVariant = Color(0xFFDEE3EA),
        onSurfaceVariant = Color(0xFF41474D),
        surfaceDim = Color(0xFFD7DADF),
        surfaceBright = Color(0xFFF6F9FE),
        surfaceContainerLowest = Color(0xFFFFFFFF),
        surfaceContainerLow = Color(0xFFF1F4F9),
        surfaceContainer = Color(0xFFEBEEF3),
        surfaceContainerHigh = Color(0xFFE5E8ED),
        surfaceContainerHighest = Color(0xFFE0E3E8),
        inverseSurface = Color(0xFF2D3135),
        inverseOnSurface = Color(0xFFEEF1F6),
        outline = Color(0xFF72787E),
        outlineVariant = Color(0xFFC1C7CE),
        scrim = Color(0xFF000000),
    )

private val AppDarkColors =
    darkColorScheme(
        primary = Color(0xFFA6C8FF),
        onPrimary = Color(0xFF003062),
        primaryContainer = Color(0xFF21477A),
        onPrimaryContainer = Color(0xFFD4E3FF),
        inversePrimary = Color(0xFF3B5F94),
        secondary = Color(0xFFB8C8DF),
        onSecondary = Color(0xFF223143),
        secondaryContainer = Color(0xFF39485B),
        onSecondaryContainer = Color(0xFFD4E3FB),
        tertiary = Color(0xFFEAB4F4),
        onTertiary = Color(0xFF481F54),
        tertiaryContainer = Color(0xFF60366C),
        onTertiaryContainer = Color(0xFFFDD6FF),
        error = Color(0xFFFFB4A9),
        onError = Color(0xFF680003),
        errorContainer = Color(0xFF930006),
        onErrorContainer = Color(0xFFFFDAD4),
        background = Color(0xFF101418),
        onBackground = Color(0xFFE0E3E8),
        surface = Color(0xFF101418),
        onSurface = Color(0xFFE0E3E8),
        surfaceVariant = Color(0xFF41474D),
        onSurfaceVariant = Color(0xFFC1C7CE),
        surfaceDim = Color(0xFF101418),
        surfaceBright = Color(0xFF363A3E),
        surfaceContainerLowest = Color(0xFF0B0F12),
        surfaceContainerLow = Color(0xFF181C20),
        surfaceContainer = Color(0xFF1C2024),
        surfaceContainerHigh = Color(0xFF262A2E),
        surfaceContainerHighest = Color(0xFF313539),
        inverseSurface = Color(0xFFE0E3E8),
        inverseOnSurface = Color(0xFF2D3135),
        outline = Color(0xFF8B9198),
        outlineVariant = Color(0xFF41474D),
        scrim = Color(0xFF000000),
    )

internal val LightColors = AppLightColors
internal val DarkColors = AppDarkColors
