package com.github.gklein7.snapgrab

interface DownloadCallbacks {
    fun isCancelled(): Boolean

    fun onProgress(percent: Int, status: String, speed: String, eta: String)
}
