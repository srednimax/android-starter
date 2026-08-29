package app.starter.data

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/**
 * DAO tests run **instrumented**, not on the JVM: Room generates real SQLite code, and there is no
 * SQLite in a plain unit test. `inMemoryDatabaseBuilder` gives each test a fresh database that
 * disappears with the process, which is why no cleanup between tests is needed beyond [close].
 */
@RunWith(AndroidJUnit4::class)
class ItemDaoTest {
    private lateinit var database: AppDatabase
    private lateinit var dao: ItemDao

    @Before
    fun open() {
        database =
            Room
                .inMemoryDatabaseBuilder(
                    ApplicationProvider.getApplicationContext(),
                    AppDatabase::class.java,
                )
                // The DAO's flows would otherwise need a background executor that the test's own
                // dispatcher does not provide. Only ever in a test.
                .allowMainThreadQueries()
                .build()
        dao = database.itemDao()
    }

    @After
    fun close() = database.close()

    @Test
    fun insertedItemsComeBackNewestFirst() =
        runTest {
            val older = ItemEntity(title = "older", createdAt = java.time.Instant.ofEpochMilli(1_000))
            val newer = ItemEntity(title = "newer", createdAt = java.time.Instant.ofEpochMilli(2_000))
            // Inserted in the wrong order on purpose: the ORDER BY is the thing under test, and a
            // test that inserts in display order passes with no ORDER BY at all.
            dao.insert(older)
            dao.insert(newer)

            assertEquals(listOf("newer", "older"), dao.all().map { it.title })
        }

    @Test
    fun theFlowReEmitsWhenARowChanges() =
        runTest {
            // This is what makes "screens collect a Flow and never call refresh" true, so it is
            // worth asserting rather than assuming.
            assertEquals(0, dao.observeAll().first().size)
            dao.insert(ItemEntity(title = "one"))
            assertEquals(1, dao.observeAll().first().size)
        }

    @Test
    fun anInstantSurvivesTheRoundTripThroughTheConverter() =
        runTest {
            val at = java.time.Instant.ofEpochMilli(1_712_345_678_901)
            dao.insert(ItemEntity(id = "fixed", title = "t", createdAt = at))
            assertEquals(at, dao.observeById("fixed").first()?.createdAt)
        }

    @Test
    fun anAbsentRowIsNullRatherThanAnEmptyItem() =
        runTest {
            assertNull(dao.observeById("nobody").first())
        }
}
