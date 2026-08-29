package app.starter.media

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.core.net.toUri
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * The media pipeline, instrumented because `Bitmap` and `BitmapFactory` are Android's.
 *
 * The claim under test is not "a file appeared" but **"the file that appeared is the reduced one"**
 * — a pipeline that silently writes the original through is the failure that costs a photo grid its
 * memory, and it looks identical from the outside.
 */
@RunWith(AndroidJUnit4::class)
class MediaFilesTest {
    private lateinit var root: File
    private lateinit var media: MediaFiles

    @Before
    fun setUp() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        root = File(context.cacheDir, "media-test-${System.nanoTime()}").apply { mkdirs() }
        media = MediaFiles(context, root)
    }

    @Test
    fun aThumbnailIsCroppedSquareAndCapped() =
        runTest {
            val source = writeJpeg(width = 1600, height = 900)
            val persisted = media.persist(source, MediaKind.Thumbnail)

            val bounds = boundsOf(media.resolve(persisted.path))
            assertEquals("square", bounds.outWidth, bounds.outHeight)
            assertTrue("capped at 512", bounds.outWidth <= 512)
        }

    @Test
    fun aPhotoKeepsItsAspectRatio() =
        runTest {
            val source = writeJpeg(width = 4000, height = 2000)
            val persisted = media.persist(source, MediaKind.Photo)

            val bounds = boundsOf(media.resolve(persisted.path))
            assertTrue("long edge capped", maxOf(bounds.outWidth, bounds.outHeight) <= 2048)
            assertEquals("2:1 kept", 2.0, bounds.outWidth.toDouble() / bounds.outHeight, 0.05)
        }

    @Test
    fun theStoredPathIsRelativeAndInTheKindsDirectory() =
        runTest {
            val persisted = media.persist(writeJpeg(200, 200), MediaKind.Photo)
            // Absolute paths change across installs and break every restored backup. This is the
            // one assertion that stops that regression at the door.
            assertTrue(persisted.path, persisted.path.startsWith("${MediaKind.Photo.directory}/"))
            assertTrue("relative", !persisted.path.startsWith("/"))
        }

    @Test
    fun anImageSmallerThanTheCapIsNotUpscaled() =
        runTest {
            val persisted = media.persist(writeJpeg(120, 120), MediaKind.Thumbnail)
            assertEquals(120, boundsOf(media.resolve(persisted.path)).outWidth)
        }

    private fun boundsOf(file: File): BitmapFactory.Options =
        BitmapFactory.Options().apply { inJustDecodeBounds = true }.also {
            BitmapFactory.decodeFile(file.path, it)
        }

    private fun writeJpeg(
        width: Int,
        height: Int,
    ): Uri {
        val file = File(root, "source-$width-$height.jpg")
        Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888).let { bitmap ->
            file.outputStream().use { bitmap.compress(Bitmap.CompressFormat.JPEG, 90, it) }
            bitmap.recycle()
        }
        return file.toUri()
    }
}
