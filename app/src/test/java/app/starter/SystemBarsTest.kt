package app.starter

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * The edge-to-edge window, held to the arrangement it actually depends on.
 *
 * `MainActivity` stopped calling `enableEdgeToEdge()` because every path in androidx.activity
 * 1.13.0 reaches `Window.setStatusBarColor` and `setNavigationBarColor`, deprecated in Android 15
 * and flagged by Play against release 386. What replaced it is a `WindowCompat` call plus theme
 * attributes plus **four** `colors.xml` files, and the four-file part is the fragile half: it is
 * load-bearing for a reason that is invisible at the call site, so it is asserted here rather than
 * left to a comment.
 *
 * **The reason is Android's qualifier precedence.** `night` outranks `vN`, so a `values-night/`
 * scrim beats a `values-v29/` transparent on an API 29+ phone in dark mode — which would hand the
 * newest half of the range a scrim it should not have, on the one configuration nobody screenshots.
 * `values-night-v29/` is what settles it, and deleting it as redundant is the exact mistake this
 * test exists to catch.
 *
 * **What it deliberately does not assert**: that no source file calls `enableEdgeToEdge()` again.
 * That would mean reading `src/main/java` off disk, and Gradle cannot see a `File(...)` opened in a
 * test body — only `src/main/res` and `translations/` are registered as test inputs
 * (`app/build.gradle.kts`), so a source-reading assertion would go stale silently and report the
 * previous run's verdict. A check that passes because it did not run is worse than no check.
 * `scripts/edge-to-edge.py` is what covers the window on a real device.
 *
 * Kotlin note: plain [File] reads and a regex rather than the DOM parser [TranslationTest] uses —
 * these are single values, and what is being asserted is that four files agree, not the shape of
 * any one of them. Gradle runs unit tests with the module directory as the working directory.
 */
class SystemBarsTest {
    /** The scrim behind the system bars, per resource qualifier, as the theme references it. */
    private fun scrim(qualifier: String): String {
        val file = File("src/main/res/$qualifier/colors.xml")
        assertTrue(
            "${file.path} does not exist. All four qualifiers must define system_bar_scrim — " +
                "see the class doc for why values-night-v29 is not redundant.",
            file.isFile,
        )
        val value =
            Regex("""<color\s+name="system_bar_scrim"\s*>([^<]+)</color>""")
                .find(file.readText())
                ?.groupValues
                ?.get(1)
        assertTrue("${file.path} does not define system_bar_scrim", value != null)
        return value!!.trim().uppercase()
    }

    @Test
    fun `the theme draws its own system bars and takes their colour from the scrim`() {
        val themes = File("src/main/res/values/themes.xml").readText()

        // Without this the platform owns the bar backgrounds and the other two items do nothing.
        assertTrue(
            "Theme.App must set windowDrawsSystemBarBackgrounds — without it the two colours " +
                "below are ignored and the app is not edge-to-edge at all.",
            themes.contains("""<item name="android:windowDrawsSystemBarBackgrounds">true</item>"""),
        )
        for (bar in listOf("statusBarColor", "navigationBarColor")) {
            assertTrue(
                "Theme.App must set android:$bar to @color/system_bar_scrim. A literal colour " +
                    "here would defeat the four qualified colours entirely.",
                themes.contains("""<item name="android:$bar">@color/system_bar_scrim</item>"""),
            )
        }
    }

    @Test
    fun `below API 29 the bars carry a scrim, because content scrolls under them`() {
        // androidx's own DefaultLightScrim and DefaultDarkScrim, copied so that dropping
        // enableEdgeToEdge() did not change any pixel. There is no contrast enforcement below 29,
        // so transparency here puts the owner's text directly behind the clock.
        assertEquals("#E6FFFFFF", scrim("values"))
        assertEquals("#801B1B1B", scrim("values-night"))
    }

    @Test
    fun `from API 29 the platform enforces contrast, so the app supplies none`() {
        assertEquals("#00000000", scrim("values-v29"))
        assertEquals(
            "values-night-v29 must be transparent too. It is not redundant with values-v29: " +
                "`night` outranks `vN` in Android's qualifier precedence, so without this file a " +
                "dark-mode phone on API 29+ resolves values-night/ and gets a scrim.",
            "#00000000",
            scrim("values-night-v29"),
        )
    }
}
