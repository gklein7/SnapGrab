package com.github.gklein7.snapgrab

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import androidx.work.getWorkInfoByIdFlow
import androidx.work.workDataOf
import com.chaquo.python.Python
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File

data class QualityOption(val value: String, val label: String)

data class MediaPreview(
    val title: String,
    val uploader: String,
    val thumbnail: String?,
    val qualityOptions: List<QualityOption>,
)

data class SnapGrabUiState(
    val url: String = "",
    val preview: MediaPreview? = null,
    val mediaType: String = "video",
    val quality: String = "best",
    val isLookingUp: Boolean = false,
    val isStartingDownload: Boolean = false,
    val errorMessage: String? = null,
)

class SnapGrabViewModel(application: Application) : AndroidViewModel(application) {
    var uiState by mutableStateOf(SnapGrabUiState())
        private set

    private val _workInfo = MutableStateFlow<WorkInfo?>(null)
    val workInfo: StateFlow<WorkInfo?> = _workInfo.asStateFlow()
    private var observation: Job? = null

    fun updateUrl(value: String) {
        uiState = uiState.copy(url = value, preview = null, errorMessage = null)
    }

    fun setSharedText(value: String?) {
        val url = MediaUrl.extract(value)
        if (url == null) {
            uiState = uiState.copy(errorMessage = "Não encontrei um link HTTP ou HTTPS nesse conteúdo.")
            return
        }
        uiState = uiState.copy(url = url, preview = null, quality = "best", errorMessage = null)
    }

    fun setMediaType(value: String) {
        if (value == "video" || value == "audio") {
            uiState = uiState.copy(mediaType = value)
        }
    }

    fun selectQuality(value: String) {
        if (uiState.preview?.qualityOptions?.any { it.value == value } == true) {
            uiState = uiState.copy(quality = value)
        }
    }

    fun lookup() {
        val url = MediaUrl.extract(uiState.url)
        if (url == null) {
            uiState = uiState.copy(errorMessage = "Digite um link HTTP ou HTTPS válido.")
            return
        }

        uiState = uiState.copy(
            url = url,
            preview = null,
            isLookingUp = true,
            errorMessage = null,
        )
        viewModelScope.launch {
            try {
                val json = withContext(Dispatchers.IO) {
                    val outputDir = File(getApplication<Application>().cacheDir, "preview")
                    Python.getInstance()
                        .getModule("snapgrab_android")
                        .callAttr(
                            "get_info_json",
                            url,
                            outputDir.absolutePath,
                            ffmpegPath(),
                        )
                        .toJava(String::class.java)
                }
                val response = JSONObject(json)
                val options = buildList {
                    val source = response.optJSONArray("quality_options")
                    if (source != null) {
                        for (index in 0 until source.length()) {
                            val option = source.optJSONObject(index) ?: continue
                            val value = option.optString("value")
                            if (value.isNotBlank()) {
                                add(QualityOption(value, option.optString("label", value)))
                            }
                        }
                    }
                    if (isEmpty()) add(QualityOption("best", "Máx."))
                }
                uiState = uiState.copy(
                    preview = MediaPreview(
                        title = response.optString("title", url),
                        uploader = response.optString("uploader"),
                        thumbnail = response.optString("thumbnail").takeIf { it.isNotBlank() && it != "null" },
                        qualityOptions = options,
                    ),
                    quality = "best",
                    isLookingUp = false,
                    errorMessage = response.optString("error").takeIf(String::isNotBlank),
                )
            } catch (error: Exception) {
                uiState = uiState.copy(
                    isLookingUp = false,
                    errorMessage = error.message ?: "Não foi possível carregar a prévia.",
                )
            }
        }
    }

    fun startDownload() {
        if (uiState.isStartingDownload || _workInfo.value?.state?.isFinished == false) return
        val url = MediaUrl.extract(uiState.url)
        if (url == null) {
            uiState = uiState.copy(errorMessage = "Digite um link HTTP ou HTTPS válido.")
            return
        }

        val request = OneTimeWorkRequestBuilder<DownloadWorker>()
            .setInputData(workDataOf(
                DownloadWorker.KEY_URL to url,
                DownloadWorker.KEY_MEDIA_TYPE to uiState.mediaType,
                DownloadWorker.KEY_QUALITY to uiState.quality,
            ))
            .build()
        uiState = uiState.copy(url = url, isStartingDownload = true, errorMessage = null)
        _workInfo.value = null

        try {
            val manager = WorkManager.getInstance(getApplication())
            manager.enqueue(request)
            observation?.cancel()
            observation = viewModelScope.launch {
                manager.getWorkInfoByIdFlow(request.id).collect { info ->
                    _workInfo.value = info
                    if (info != null) uiState = uiState.copy(isStartingDownload = false)
                }
            }
        } catch (error: Exception) {
            uiState = uiState.copy(
                isStartingDownload = false,
                errorMessage = error.message ?: "Não foi possível iniciar o download.",
            )
        }
    }

    fun cancelDownload() {
        val workId = _workInfo.value?.id ?: return
        WorkManager.getInstance(getApplication()).cancelWorkById(workId)
    }

    private fun ffmpegPath(): String =
        File(getApplication<Application>().applicationInfo.nativeLibraryDir, "libffmpeg.so").absolutePath
}
