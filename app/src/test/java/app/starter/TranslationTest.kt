package app.starter

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.w3c.dom.Element
import java.io.File
import javax.xml.parsers.DocumentBuilderFactory

/**
 * Every shipped translation against the English base, checked mechanically (ADR-0004).
 *
 * Was `PolishTranslationTest`, which held one language. The assertions were already the right ones;
 * what changed is that the language is now a **row in a table** rather than a field, so the ninth
 * language costs a line of `locales_config.xml` and a CLDR entry instead of a new test file.
 *
 * **Completeness is deliberately not here.** "Every base string has a counterpart in every locale"
 * used to be this file's first assertion, and at nine languages it would put every feature branch
 * behind a translation round — you could not add an English string and build until seven other
 * languages had caught up, which is how translation gets done twice: once against the draft copy
 * and again after review reworded it. It moved to `scripts/translation-gate.py`, which CI runs on
 * every pull request. The rule is unchanged and the boundary moved: **free while you work, strict
 * before it merges.**
 *
 * What stays here is everything that must hold for whatever *is* translated, at any moment — a
 * half-translated file is fine, a wrongly-translated one is not.
 *
 * Kotlin note: the XML is parsed with the JDK's own DOM parser rather than Android's, because a
 * `src/test` unit test runs on the JVM with no Android framework under it — the same reason
 * [app.starter.ui.settings.AppLanguageTest] reads its resource as a plain [File]. Gradle runs
 * unit tests with the module directory as the working directory.
 */
class TranslationTest {
    private val base = parse(BASE_STRINGS)

    /** The locales this build actually ships, read from the file the platform itself reads. */
    private val shipped: List<String> =
        Regex("""<locale\s+android:name="([^"]+)"""")
            .findAll(File(LOCALES_CONFIG).readText())
            .map { it.groupValues[1] }
            .toList()

    /**
     * Drafts staged outside `res/`, one directory per BCP-47 tag.
     *
     * Resource resolution never consults `locales_config.xml`, so the moment `values-de/` exists
     * every phone set to German gets those strings, reviewed or not. A draft therefore lands here
     * and promotion is a file move.
     */
    private val staged: List<String> =
        File(STAGED)
            .listFiles()
            ?.filter { it.isDirectory }
            ?.map { it.name }
            ?.sorted()
            .orEmpty()

    /**
     * Everything checked below: every shipped locale except the base one, and every staged draft.
     *
     * A draft is held to exactly the same rules as a shipped translation — that is what staging it
     * in the repository buys over reviewing it in a spreadsheet. The one rule it is *not* held to
     * is completeness, which belongs to `scripts/translation-gate.py` and to shipped languages.
     */
    private val translations: List<Translation>
        get() =
            shipped.filterNot { it == BASE_LOCALE }.map {
                Translation(it, "values-${qualifier(it)}", parse(stringsFor(it)))
            } +
                staged.map {
                    // Labelled from the repository root rather than from `STAGED`, whose leading
                    // `..` is an artefact of the working directory and not part of the path anyone
                    // would type.
                    Translation(it, "translations/$it/strings.xml", parse(stagedFor(it)))
                }

    @Test
    fun `every shipped locale has a resource directory and a plural table`() {
        // Three declarations of one list — locales_config.xml, the AppLanguage enum and the res
        // directory — and this is the one that catches the spelling. A BCP-47 tag writes a region
        // plainly (`pt-BR`); a resource qualifier prefixes it with `r` (`values-pt-rBR`). Two
        // spellings of one locale in two files is exactly the mistake that ships a language the
        // app declares and cannot load, and it is silent: resource resolution simply falls back to
        // English and nothing anywhere fails.
        shipped.forEach { tag ->
            assertTrue(
                "no CLDR plural categories recorded for '$tag' — add its row to CLDR_PLURALS. " +
                    "A missing category is not an error at run time: it silently resolves to " +
                    "'other' and renders a grammatically wrong sentence.",
                tag in CLDR_PLURALS,
            )
            if (tag != BASE_LOCALE) {
                val file = File(stringsFor(tag))
                assertTrue(
                    "locales_config.xml declares '$tag' but ${file.path} does not exist. " +
                        "Note the qualifier spelling: a region takes an 'r' prefix, so the tag " +
                        "'pt-BR' lives in 'values-pt-rBR'.",
                    file.isFile,
                )
            }
        }
    }

    @Test
    fun `every staged draft is a language the app could ship, and is staged only once`() {
        // A draft's directory name is a claim about which language it is, and two of the three
        // checks below exist because that claim is otherwise never tested: a typo'd tag would be
        // drafted, reviewed and promoted into a `values-` directory no phone ever resolves.
        staged.forEach { tag ->
            assertTrue(
                "translations/$tag drafts a locale with no CLDR plural row — add it to " +
                    "CLDR_PLURALS before drafting, or its plurals go unchecked.",
                tag in CLDR_PLURALS,
            )
            assertTrue(
                "'$tag' is staged in translations/$tag *and* shipped in values-${qualifier(tag)}. " +
                    "Promotion is a move, not a copy: two files for one language drift, and res/ " +
                    "is the one the phone reads.",
                tag !in shipped,
            )
            assertTrue(
                "translations/$tag exists but holds no strings.xml.",
                File(stagedFor(tag)).isFile,
            )
        }
    }

    @Test
    fun `no translated file declares a resource the base language does not`() {
        // The reverse drift: a resource renamed in `values/` and left behind in a translation
        // resolves to nothing, silently, because the base file is what the R class is generated
        // from. Unlike a missing translation, this one is never visible on screen.
        translations.forEach { (_, label, translated) ->
            val orphaned = translated.all.keys - base.all.keys
            assertTrue(
                "$label declares resources the base language does not: ${orphaned.sorted()}",
                orphaned.isEmpty(),
            )
        }
    }

    @Test
    fun `nothing marked untranslatable appears in a translated file`() {
        // `translatable="false"` means locale-*invariant*: the launcher label, the endonyms, a
        // medicine's brand name. A copy in a translated file resolves fine and renders the same
        // words, so nothing is ever visibly wrong — it just costs a line per language, forever,
        // and every future translator reads past it. At nine languages the endonyms alone would
        // have been 81 duplicated entries.
        translations.forEach { (_, label, translated) ->
            val copied = base.untranslatable intersect translated.all.keys
            assertTrue(
                "$label translates resources the base language marks " +
                    "translatable=\"false\": ${copied.sorted()} — delete them there, or drop the " +
                    "marker in values/strings.xml",
                copied.isEmpty(),
            )
        }
    }

    @Test
    fun `the launcher label is deliberately untranslated and stays that way`() {
        // A launcher label resolves against the *system* locale, not the app's, so a translated
        // app_name would rename the icon on a Polish phone whose owner set the app to English. The
        // exemption has to be *declared* in the base file, which is the half the general rule above
        // cannot check: a deleted marker makes app_name translatable again and every assertion here
        // still passes, right up until a translator obliges.
        assertTrue(
            "app_name should be marked translatable=\"false\" in the base language",
            "app_name" in base.untranslatable,
        )
    }

    @Test
    fun `every translated string keeps the base language's format arguments`() {
        // A dropped %1$s is not a typo — the argument is still passed at the call site, so the
        // sentence renders without the interpolated name and nothing anywhere fails.
        //
        // Note what this cannot see: an argument that is *kept* and given a different job. Polish
        // `photo_gallery_empty_help` carried its %1$s faithfully and moved it from the thing the
        // photos are of to the gallery they land in, describing a folder that does not exist. Every
        // assertion here passed. That half is the native read-through's, and always will be.
        translations.forEach { (_, label, translated) ->
            base.strings.forEach { (name, element) ->
                val counterpart = translated.strings[name] ?: return@forEach
                assertEquals(
                    "format arguments differ for string '$name' in $label",
                    element.formatArguments(),
                    counterpart.formatArguments(),
                )
            }
            base.plurals.forEach { (name, element) ->
                // Compared against the base's `other` item: English has two categories and Polish
                // four, so there is no item-for-item pairing to make — every translated item has to
                // carry the same arguments as the English sentence it is a form of.
                val expected =
                    element
                        .items()
                        .first { it.getAttribute("quantity") == "other" }
                        .formatArguments()
                translated.plurals[name]?.items()?.forEach { item ->
                    assertEquals(
                        "format arguments differ for plural '$name', quantity " +
                            "'${item.getAttribute("quantity")}' in $label",
                        expected,
                        item.formatArguments(),
                    )
                }
            }
        }
    }

    @Test
    fun `every translated plural covers exactly its language's CLDR categories`() {
        // Counts go through <plurals> and never through concatenation, which is the whole point of
        // ADR-0004's consequence — and a plural is only as good as its category list. Checked
        // against the language's *own* rules rather than a hardcoded set of four: Polish needs
        // one/few/many/other where German needs one/other, and requiring four of German would be as
        // wrong as requiring two of Polish.
        translations.forEach { (tag, label, translated) ->
            val required = CLDR_PLURALS.getValue(tag)
            translated.plurals.forEach { (name, element) ->
                val quantities =
                    element
                        .items()
                        .mapNotNull { it.getAttribute("quantity").takeIf(String::isNotEmpty) }
                        .toSet()
                assertEquals(
                    "plural '$name' in $label does not carry exactly the " +
                        "categories CLDR gives '$tag'",
                    required,
                    quantities,
                )
            }
        }
    }

    @Test
    fun `every string array has the same number of items in every locale`() {
        // A `<string-array>` is usually a list the code indexes into or zips against something else,
        // so a translation that has gained or lost an entry is a bug whichever way it drifted — and
        // it is invisible to every other check here, because each individual item is well formed.
        //
        // An entry with no local form legitimately stays in its original language. That is a
        // translation decision, not a missing item, and it keeps the lengths equal.
        base.arrays.forEach { (name, baseArray) ->
            val expected = baseArray.items().size
            translations.forEach { (_, label, translated) ->
                val array = translated.arrays[name] ?: return@forEach
                assertEquals("$name in $label has drifted in length", expected, array.items().size)
            }
        }
    }

    private fun parse(path: String): Resources {
        val file = File(path)
        assertTrue("$path not found at ${file.absolutePath} — has the resource moved?", file.exists())
        val document =
            DocumentBuilderFactory
                .newInstance()
                .newDocumentBuilder()
                .parse(file)

        fun named(tag: String) =
            document
                .getElementsByTagName(tag)
                .let { nodes -> (0 until nodes.length).map { nodes.item(it) as Element } }
                // Only top-level declarations: <item> lives inside these and is read separately.
                .filter { it.hasAttribute("name") }
                .associateBy { it.getAttribute("name") }
        return Resources(named("string"), named("plurals"), named("string-array"))
    }

    /**
     * One translation under test, wherever it lives.
     *
     * [label] is what a failure message names, and it is the file's own path rather than a derived
     * one: "values-de" and "translations/de/strings.xml" are two different claims about a language,
     * and an assertion that pointed at the wrong one would send someone editing a file that is not
     * the problem.
     */
    private data class Translation(
        val tag: String,
        val label: String,
        val resources: Resources,
    )

    /**
     * One `strings.xml`, split by resource kind.
     *
     * Kotlin note: a `data class` here is closer to a TS interface than to a class — it exists for
     * the named fields and the copy/equals that come free, not for behaviour.
     */
    private data class Resources(
        val strings: Map<String, Element>,
        val plurals: Map<String, Element>,
        val arrays: Map<String, Element>,
    ) {
        val all: Map<String, Element> get() = strings + plurals + arrays

        /** Marked `translatable="false"`: never expected in a `values-<locale>` folder. */
        val untranslatable: Set<String>
            get() = all.filterValues { it.getAttribute("translatable") == "false" }.keys
    }

    private companion object {
        const val BASE_LOCALE = "en"
        const val BASE_STRINGS = "src/main/res/values/strings.xml"
        const val LOCALES_CONFIG = "src/main/res/xml/locales_config.xml"

        /**
         * Where a language waits for its native read-through. One directory up, because it is a
         * repository-level staging area rather than an Android source set — and outside `res/`
         * precisely so that a draft cannot be shipped by existing.
         */
        const val STAGED = "../translations"

        /**
         * Plural categories per language, from CLDR.
         *
         * One row per shipped language; only the locales named in
         * `locales_config.xml` are actually asserted, so a row here is ready rather than active.
         * **Verify the row when its language lands** — this table is written from CLDR's rules, not
         * read out of the tool, and a wrong row fails in the one direction nothing notices.
         *
         * The romance `many` is a large-number form and is unreachable for the integer counts this
         * app produces. It is declared anyway, for the same reason Polish declares `other`: Android
         * resolves against the declaration, and a category that is missing renders blank rather
         * than falling back to something sensible.
         */
        val CLDR_PLURALS =
            mapOf(
                "en" to setOf("one", "other"),
                "de" to setOf("one", "other"),
                "es" to setOf("one", "many", "other"),
                "fr" to setOf("one", "many", "other"),
                "it" to setOf("one", "many", "other"),
                "pt-BR" to setOf("one", "many", "other"),
                "pl" to setOf("one", "few", "many", "other"),
                "cs" to setOf("one", "few", "many", "other"),
                "uk" to setOf("one", "few", "many", "other"),
            )

        /**
         * The `values-` qualifier for a BCP-47 tag: `pl` → `pl`, `pt-BR` → `pt-rBR`.
         *
         * The `r` prefix on the region is the whole reason this function exists rather than being
         * string interpolation at the call sites — the tag and the directory are two spellings of
         * one locale, which is the shape of mistake to expect.
         */
        fun qualifier(tag: String): String =
            tag.split('-').let { parts ->
                if (parts.size == 2) "${parts[0]}-r${parts[1]}" else tag
            }

        fun stringsFor(tag: String) = "src/main/res/values-${qualifier(tag)}/strings.xml"

        /** A staged draft keeps the BCP-47 tag itself — no `r` prefix, because it is not a qualifier. */
        fun stagedFor(tag: String) = "$STAGED/$tag/strings.xml"

        /** `%1$s`, `%2$d`, and the non-positional `%d` that single-argument plurals use. */
        val FORMAT_ARGUMENT = Regex("""%(\d+\$)?[a-zA-Z]""")

        fun Element.items(): List<Element> =
            getElementsByTagName("item")
                .let { nodes -> (0 until nodes.length).map { nodes.item(it) as Element } }

        /** Sorted, because a translation may legitimately reorder arguments — that is what `%1$s` is for. */
        fun Element.formatArguments(): List<String> =
            FORMAT_ARGUMENT
                .findAll(textContent)
                .map { it.value }
                .sorted()
                .toList()
    }
}
