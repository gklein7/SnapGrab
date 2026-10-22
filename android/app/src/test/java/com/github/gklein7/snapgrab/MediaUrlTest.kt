package com.github.gklein7.snapgrab

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class MediaUrlTest {
    @Test
    fun extractsSharedUrlAndRemovesTrailingPunctuation() {
        assertEquals(
            "https://www.youtube.com/watch?v=abc123",
            MediaUrl.extract("Veja este vídeo: https://www.youtube.com/watch?v=abc123."),
        )
    }

    @Test
    fun acceptsOnlyHttpUrlsWithAHostAndWithoutCredentials() {
        assertNull(MediaUrl.extract("file:///sdcard/video.mp4"))
        assertNull(MediaUrl.extract("https:///missing-host"))
        assertNull(MediaUrl.extract("https://user:pass@example.com/video"))
    }

    @Test
    fun returnsNullWhenTextHasNoUrl() {
        assertNull(MediaUrl.extract("texto sem link"))
    }
}
