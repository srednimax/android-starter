package app.starter.ui.settings

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * The switcher's list and `locales_config.xml` are the same claim written twice (ADR-0004), and
 * this is what stops them drifting.
 *
 * They cannot be one file: the XML is a build-time resource the platform and AppCompat read
 * directly, and the enum is what the Settings row iterates. So the duplication is forced, and the
 * failure it invites is silent — a `values-pl/` folder plus a `locales_config` entry with no
 * [AppLanguage] entry ships a translation the in-app switcher cannot reach, and the reverse offers
 * a language the system will not honour. Both would otherwise be found by hand, in the week the
 * translation lands, which is the worst possible week to find them.
 *
 * Reads the resource off disk rather than through `R`, deliberately: an XML resource is not
 * readable from a JVM unit test without Robolectric, and the file is the artifact whose contents
 * are in question. Gradle runs unit tests with the module directory as the working directory.
 */
class AppLanguageTest {
    @Test
    fun `the switcher offers exactly the languages the app declares`() {
        val config = File("src/main/res/xml/locales_config.xml")
        assertTrue(
            "locales_config.xml not found at ${config.absolutePath} — has the resource moved?",
            config.isFile,
        )

        val declared =
            Regex("""<locale\s+android:name="([^"]+)"""")
                .findAll(config.readText())
                .map { it.groupValues[1] }
                .toSet()

        assertEquals(declared, AppLanguage.entries.map { it.tag }.toSet())
    }

    @Test
    fun `english is the base language and is always offered`() {
        // ADR-0004: English is the fallback for every unmatched locale, so it is the one entry that
        // cannot be removed without changing what an unlisted language falls back to.
        assertTrue(AppLanguage.entries.any { it.tag == "en" })
    }

    @Test
    fun `no two languages share a language subtag`() {
        // What `currentAppLanguage()` leans on. It matches the platform's locale against the
        // **language subtag** of each entry rather than the whole tag, because the platform reports
        // `pt-BR` as plain "pt" and may report `en` as "en-GB" — whole-tag comparison misses both,
        // and the symptom is a chip the user just tapped that never looks selected.
        //
        // That match is sound only while the subtags are unique. A second Portuguese or a second
        // Spanish would make it ambiguous rather than merely wrong: two entries would answer to the
        // same locale and `firstOrNull` would silently pick whichever is declared first. The fix
        // then is to match on the full tag with a subtag fallback — not to delete this test.
        val subtags = AppLanguage.entries.map { it.tag.substringBefore('-') }
        assertEquals(
            "two languages share a language subtag, which makes currentAppLanguage() ambiguous: " +
                subtags.groupBy { it }.filterValues { it.size > 1 }.keys,
            subtags.size,
            subtags.toSet().size,
        )
    }
}
