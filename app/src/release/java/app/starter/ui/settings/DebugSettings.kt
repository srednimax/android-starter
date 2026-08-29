package app.starter.ui.settings

import androidx.compose.runtime.Composable

/**
 * The release half of the developer-surface seam: nothing at all.
 *
 * **Why a source set rather than `if (BuildConfig.DEBUG)`.** With `isMinifyEnabled = false` — which
 * is the default, and what a lot of apps ship with — a statically-false branch is still *compiled
 * into the release binary*. That is a hide, not a strip: the code is there to be found, and any
 * strings it references are still in `res/values/strings.xml`, which means they are still inside the
 * translation gate and you end up paying to translate a debug menu.
 *
 * Two files with the same signature costs one no-op and removes the whole class of problem. Debug
 * strings live in `src/debug/res/` marked `translatable="false"`, so Android lint stays quiet too.
 */
@Composable
fun DebugSettings() = Unit
