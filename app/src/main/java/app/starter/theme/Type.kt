package app.starter.theme

import androidx.compose.material3.Typography

/**
 * The type scale.
 *
 * Deliberately M3's own defaults — Roboto on Android — because a typeface is a brand decision the
 * template has no business making for you, and shipping a font you did not choose is also a licence
 * obligation you did not choose.
 *
 * ## Adding a display face
 *
 * The usual shape is: a decorative family for `display*` and `headline*` only, and
 * `FontFamily.Default` for everything else. That keeps the personality in the two or three places
 * a reader notices it and leaves body text to the system font, which is what the platform has
 * already optimised for legibility at small sizes.
 *
 * ```kotlin
 * private val Display =
 *     FontFamily(
 *         Font(R.font.yourface_bold, weight = FontWeight.Bold),
 *         Font(R.font.yourface_extrabold, weight = FontWeight.ExtraBold),
 *     )
 * ```
 *
 * **The trap, if the font is a variable font** — one file with a continuous `wght` axis rather than
 * one file per weight, which is how most families now ship. Android has supported those since API
 * 26 (this project's `minSdk`), but Compose's `FontVariation.Settings` is *silently ignored* for
 * resource fonts. Set the axis that way and the family renders at the font's default instance —
 * often ExtraLight — looking thinner than the Roboto it replaced, with no error anywhere. The fix
 * is one XML font resource per weight, each pinning `android:fontVariationSettings="'wght' 700"`,
 * registered here as separate `Font(...)` entries pointing at the same `.ttf`.
 *
 * **Leave a role out rather than restating its default.** Naming `titleSmall` here with M3's own
 * value freezes it: the Material baseline moves with the BOM, and a copy of it does not.
 */
val Typography = Typography()
