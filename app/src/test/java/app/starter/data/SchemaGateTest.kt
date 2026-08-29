package app.starter.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * **The launch decision as a truth table** — and the test that is easiest to leave unwritten.
 *
 * A migration test opens the database *directly*. `MigrationTestHelper`, a release-shaped open, a
 * committed backup archive: all of them are true, and **none of them touches the gate in front of
 * Room**, which is where a user updating from Play actually arrives. An app can ship a refusal
 * screen to every existing install with a completely green migration suite behind it. This file is
 * the other half.
 *
 * Two kinds of test live here, and it is worth keeping them apart:
 *
 * - **The rule**, exercised against example migration lists. Those never change.
 * - **This app's own registered set**, in [the shipped migrations reach this build's version]. That
 *   one you extend on every schema bump — and `scripts/schema-gate.py` will not let a bump merge
 *   without it.
 */
class SchemaGateTest {
    /** What this build really ships, so the assertion below cannot drift from the registered set. */
    private val shipped = APP_MIGRATION_STEPS

    /**
     * **Extend this on every schema bump.**
     *
     * List every schema version a *released* build ever wrote, and assert each can reach the
     * current one. The skipped-version case is the one that bites: a phone that sat on version 1
     * through three releases upgrades straight to 4, walking three migrations in a row, and nobody
     * ever tests that path by hand.
     *
     * At schema 1 there is nothing to walk yet, so this asserts the honest thing — that the set is
     * empty *because* the app has only ever written one version. The moment [APP_SCHEMA_VERSION]
     * climbs, replace this with the real list.
     */
    @Test
    fun `the shipped migrations reach this build's version`() {
        if (APP_SCHEMA_VERSION == 1) {
            assertTrue(
                "schema 1 has nothing to migrate from — replace this with the real list on the first bump",
                shipped.isEmpty(),
            )
            return
        }
        for (from in 1 until APP_SCHEMA_VERSION) {
            assertTrue(
                "$from → $APP_SCHEMA_VERSION is not reachable by the registered migrations",
                migrationPathExists(from, APP_SCHEMA_VERSION, shipped),
            )
        }
    }

    // ---------------------------------------------------------------------------------------
    // The rule itself, against example lists. These do not change as the app's schema climbs.
    // ---------------------------------------------------------------------------------------

    private val example = listOf(1 to 2, 2 to 3, 3 to 4)

    @Test
    fun `a chain of steps walks the whole way`() {
        assertTrue("1 → 4", migrationPathExists(1, 4, example))
        assertTrue("2 → 4", migrationPathExists(2, 4, example))
    }

    @Test
    fun `a version nothing starts at is not reachable`() {
        // The disposable era: versions wiped rather than migrated leave no migration starting there.
        assertFalse("0 → 4", migrationPathExists(0, 4, example))
    }

    @Test
    fun `no path runs backwards, however many steps exist forwards`() {
        assertFalse("a downgrade", migrationPathExists(4, 3, example))
        assertFalse("nowhere to go", migrationPathExists(4, 4, example))
    }

    @Test
    fun `a step that skips a version counts, because Room would take it`() {
        assertTrue("1 → 3 in one jump", migrationPathExists(1, 3, listOf(1 to 3)))
        // …but never past the target: a 1 → 5 migration cannot land a file on a build that is at 4.
        assertFalse("overshooting", migrationPathExists(1, 4, listOf(1 to 5)))
    }

    @Test
    fun `an ordinary launch opens, with or without migrations`() {
        assertEquals(
            "a fresh install has no file",
            SchemaGate.Open,
            schemaGateDecision(onDiskVersion = 0, appSchemaVersion = 4, steps = example, destructiveAllowed = false),
        )
        assertEquals(
            "already at this build's shape",
            SchemaGate.Open,
            schemaGateDecision(onDiskVersion = 4, appSchemaVersion = 4, steps = example, destructiveAllowed = false),
        )
    }

    @Test
    fun `a user updating across a schema bump is let in, and Room migrates`() {
        assertEquals(
            "one bump behind — the upgrade every existing user is about to take",
            SchemaGate.Open,
            schemaGateDecision(onDiskVersion = 3, appSchemaVersion = 4, steps = example, destructiveAllowed = false),
        )
        assertEquals(
            "and the skipped-version upgrade, from a phone that sat out two releases",
            SchemaGate.Open,
            schemaGateDecision(onDiskVersion = 1, appSchemaVersion = 4, steps = example, destructiveAllowed = false),
        )
    }

    @Test
    fun `a release build still refuses what it genuinely cannot read`() {
        assertEquals(
            "no migration starts at 0 with a file present",
            SchemaGate.Refuse,
            schemaGateDecision(onDiskVersion = 9, appSchemaVersion = 4, steps = example, destructiveAllowed = false),
        )
    }

    /**
     * The same decision is what background entry points ask before touching anything
     * (`schemaBlocksBackgroundWork`), so the three answers are worth stating in those terms.
     *
     * `Open` is the interesting one. A worker that sat out *any* mismatch — including an upgrade the
     * next database open was about to perform anyway — is what leaves the first reminder after an
     * update unposted, and the chain stopped until someone opens the app.
     */
    @Test
    fun `background work is blocked by exactly the decisions that are not Open`() {
        val migratableUpgrade =
            schemaGateDecision(onDiskVersion = 3, appSchemaVersion = 4, steps = example, destructiveAllowed = false)
        val debugWipe =
            schemaGateDecision(onDiskVersion = 3, appSchemaVersion = 4, steps = example, destructiveAllowed = true)
        val unreadable =
            schemaGateDecision(onDiskVersion = 9, appSchemaVersion = 4, steps = example, destructiveAllowed = false)

        assertEquals("a worker may run through an upgrade it can migrate", SchemaGate.Open, migratableUpgrade)
        assertTrue("but never through a wipe with nobody looking", debugWipe != SchemaGate.Open)
        assertTrue("and never over a file it cannot read", unreadable != SchemaGate.Open)
    }

    /**
     * The branch order in `schemaGateDecision`, stated as its own claim.
     *
     * A debug build registers **no** migrations — it takes the destructive fallback instead, and Room
     * prefers a registered migration over the fallback, so a build has one or the other and never
     * both. A gate that asked "is there a path?" before "does this build wipe?" would send a debug
     * build straight past the consent screen and let Room empty the file in silence.
     */
    @Test
    fun `a debug build still consents before it wipes, even where a migration exists on paper`() {
        assertEquals(
            SchemaGate.Consent,
            schemaGateDecision(onDiskVersion = 3, appSchemaVersion = 4, steps = example, destructiveAllowed = true),
        )
        assertEquals(
            "but an untouched file is still just a launch",
            SchemaGate.Open,
            schemaGateDecision(onDiskVersion = 4, appSchemaVersion = 4, steps = example, destructiveAllowed = true),
        )
    }
}
