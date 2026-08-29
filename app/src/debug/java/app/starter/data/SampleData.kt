package app.starter.data

/**
 * Rows to develop and screenshot against. Debug-only.
 *
 * **Deterministic on purpose** — the same titles in the same order every time. A seeder that
 * randomises produces a different screenshot on every run, which makes an image diff useless and
 * turns a screenshot suite from a check into decoration.
 */
object SampleData {
    private val titles =
        listOf(
            "First item",
            "Second item",
            "An item with a longer title, to see how a row wraps",
        )

    suspend fun seed(repository: ItemRepository) {
        wipe(repository)
        for ((index, title) in titles.withIndex()) {
            repository.save(
                ItemEntity(
                    title = title,
                    notes = if (index == 0) "Some notes, so the list has two lines in it." else null,
                ),
            )
        }
    }

    suspend fun wipe(repository: ItemRepository) {
        for (item in repository.all()) repository.delete(item)
    }
}
