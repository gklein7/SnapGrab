package com.github.gklein7.snapgrab

import java.net.URI

internal object MediaUrl {
    private val pattern = Regex("https?://[^\\s<>\"']+", RegexOption.IGNORE_CASE)

    fun extract(text: String?): String? {
        val candidate = pattern.find(text.orEmpty())?.value
            ?.trimEnd(',', '.', ';', '!', '?', ')', ']', '}')
            ?: return null
        val uri = runCatching { URI(candidate) }.getOrNull() ?: return null
        val scheme = uri.scheme?.lowercase() ?: return null
        if (scheme != "http" && scheme != "https") return null
        if (uri.host.isNullOrBlank() || uri.userInfo != null) return null
        return candidate
    }
}
