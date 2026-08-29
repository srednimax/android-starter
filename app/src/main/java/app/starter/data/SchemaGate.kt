package app.starter.data

/**
 * **What a launch should do about the database that is already on the phone** (ADR-0001).
 *
 * The guard used to ask one question — "is the file at this build's version?" — and treat every
 * answer of "no" the same way. That is right for a background worker, which must not touch a file it
 * has not been told about, and wrong for a launch: it cannot tell *a version this build must not
 * open* from *a version this build has not opened yet*, and an ordinary upgrade is the second one.
 * The cost of the conflation was total: a user updating across a schema bump met the refusal
 * screen, and the migration the project had tested never ran. It is worth reading twice: the two
 * failing cases look identical from inside the guard, and only one of them is a real problem.
 */
enum class SchemaGate {
    /** Open the database. Room applies any registered migration on the way in. */
    Open,

    /** Show the consent screen, then wipe — a debug build with no migration to offer (ADR-0001). */
    Consent,

    /** Show the refusal screen and stop. A release build that genuinely cannot read this file. */
    Refuse,
}

/**
 * Whether the registered migrations can walk [from] up to [to].
 *
 * Takes plain `start to end` pairs rather than Room's `Migration` objects so the rule is a pure
 * function over integers — testable on the JVM without Room, and honest about being nothing more
 * than reachability. Breadth-first rather than "does every consecutive step exist", because Room
 * itself is allowed to take a migration that skips versions, and a rule that is stricter than Room
 * would refuse a file Room could actually open.
 *
 * Downgrades are never reachable: no migration runs backwards, which is why [from] `>=` [to] is
 * false rather than an error.
 */
fun migrationPathExists(
    from: Int,
    to: Int,
    steps: List<Pair<Int, Int>>,
): Boolean {
    if (from >= to) return false

    val outgoing = steps.groupBy { (start, _) -> start }
    val seen = mutableSetOf(from)
    val queue = ArrayDeque(listOf(from))

    while (queue.isNotEmpty()) {
        val at = queue.removeFirst()
        if (at == to) return true
        for ((_, end) in outgoing[at].orEmpty()) {
            // Never step past the target: a migration ending above this build's version would leave
            // the file at a shape this build does not have.
            if (end <= to && seen.add(end)) queue.addLast(end)
        }
    }
    return false
}

/**
 * The launch decision, as one pure function so it can be a truth table in a test rather than a
 * behaviour discovered on a phone.
 *
 * **The order of the branches is the whole design.** `destructiveAllowed` is asked *before* the
 * migrations, because a build takes migrations **or** the fallback and never both (ADR-0001): a debug build has no migration registered at all, so a path that exists on
 * paper is not one that build can walk. Asking about migrations first would send a debug build
 * through `Open` and let Room empty the file with no consent screen — the exact thing ADR-0001
 * forbids.
 *
 * @param onDiskVersion the `user_version` out of the file header, `0` when there is no file yet.
 * @param steps the migrations this build has actually registered, as `start to end`.
 */
fun schemaGateDecision(
    onDiskVersion: Int,
    appSchemaVersion: Int = APP_SCHEMA_VERSION,
    steps: List<Pair<Int, Int>> = APP_MIGRATION_STEPS,
    destructiveAllowed: Boolean = destructiveMigrationAllowed(),
): SchemaGate =
    when {
        // Nothing there, or already this build's shape. The ordinary launch, and much the commonest.
        !schemaMismatchPending(onDiskVersion, appSchemaVersion) -> SchemaGate.Open
        destructiveAllowed -> SchemaGate.Consent
        migrationPathExists(onDiskVersion, appSchemaVersion, steps) -> SchemaGate.Open
        else -> SchemaGate.Refuse
    }

/** [APP_MIGRATIONS] as the integer pairs [schemaGateDecision] reasons over. */
val APP_MIGRATION_STEPS: List<Pair<Int, Int>> =
    APP_MIGRATIONS.map { migration -> migration.startVersion to migration.endVersion }
