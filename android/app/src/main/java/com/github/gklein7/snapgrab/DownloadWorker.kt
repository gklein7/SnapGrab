package com.github.gklein7.snapgrab

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.ContentValues
import android.content.Context
import android.content.pm.ServiceInfo
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.webkit.MimeTypeMap
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.work.CoroutineWorker
import androidx.work.ForegroundInfo
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.chaquo.python.Python
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean

class DownloadWorker(
    context: Context,
    parameters: WorkerParameters,
) : CoroutineWorker(context, parameters) {
    private val cancelRequested = AtomicBoolean(false)
    private val notificationId = id.hashCode().and(Int.MAX_VALUE).coerceAtLeast(1)

    override fun onStopped() {
        cancelRequested.set(true)
        super.onStopped()
    }

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val url = inputData.getString(KEY_URL)
            ?: return@withContext failure("O link do download está vazio.")
        val mediaType = inputData.getString(KEY_MEDIA_TYPE) ?: "video"
        val quality = inputData.getString(KEY_QUALITY) ?: "best"
        val workDir = File(applicationContext.filesDir, "downloads/$id")

        try {
            if (!workDir.mkdirs() && !workDir.isDirectory) {
                return@withContext failure("Não foi possível preparar o download.")
            }

            createNotificationChannel()
            setForeground(ForegroundInfo(
                notificationId,
                buildNotification(null, "Preparando download…"),
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC,
            ))

            val ffmpegPath = File(applicationContext.applicationInfo.nativeLibraryDir, "libffmpeg.so")
            check(ffmpegPath.isFile) { "O FFmpeg não está disponível neste aparelho." }

            val callbacks = object : DownloadCallbacks {
                override fun isCancelled(): Boolean = cancelRequested.get() || isStopped

                override fun onProgress(percent: Int, status: String, speed: String, eta: String) {
                    val details = when (status) {
                        "downloading" -> listOf(speed, eta).filter(String::isNotBlank).joinToString(" · ")
                        "processing" -> "Preparando o arquivo…"
                        "cancelled" -> "Cancelando download…"
                        else -> "Baixando…"
                    }
                    setProgressAsync(workDataOf(
                        KEY_PERCENT to percent.coerceIn(0, 100),
                        KEY_STATUS to details,
                    ))
                    try {
                        NotificationManagerCompat.from(applicationContext)
                            .notify(notificationId, buildNotification(percent, details))
                    } catch (_: SecurityException) {
                        // Android may hide notifications if the user denied POST_NOTIFICATIONS.
                    }
                }
            }

            val bridge = Python.getInstance().getModule("snapgrab_android")
            val response = bridge.callAttr(
                "download_json",
                url,
                workDir.absolutePath,
                ffmpegPath.absolutePath,
                mediaType,
                quality,
                callbacks,
            ).toJava(String::class.java)
            val result = JSONObject(response)

            if (cancelRequested.get() || isStopped || result.optBoolean("cancelled")) {
                return@withContext failure("Download cancelado.")
            }
            if (!result.optBoolean("success")) {
                return@withContext failure(result.optString("error", "O download falhou."))
            }

            val output = File(result.getString("filename")).canonicalFile
            check(output.toPath().startsWith(workDir.canonicalFile.toPath())) {
                "O caminho do arquivo baixado não é válido."
            }
            check(output.isFile && output.length() > 0L) { "O arquivo final não foi encontrado." }

            setProgressAsync(workDataOf(KEY_PERCENT to 100, KEY_STATUS to "Salvando em Downloads…"))
            val publishedUri = publishToDownloads(output, mediaType)
            Result.success(workDataOf(KEY_URI to publishedUri.toString(), KEY_NAME to output.name))
        } catch (cancelled: CancellationException) {
            cancelRequested.set(true)
            throw cancelled
        } catch (error: Exception) {
            failure(error.message ?: "Ocorreu um erro durante o download.")
        } finally {
            workDir.deleteRecursively()
        }
    }

    private fun failure(message: String) = Result.failure(workDataOf(KEY_ERROR to message))

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Downloads do SnapGrab",
                NotificationManager.IMPORTANCE_LOW,
            )
            applicationContext.getSystemService(NotificationManager::class.java)
                .createNotificationChannel(channel)
        }
    }

    private fun buildNotification(progress: Int?, content: String) =
        NotificationCompat.Builder(applicationContext, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle("SnapGrab")
            .setContentText(content)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setProgress(100, progress?.coerceIn(0, 100) ?: 0, progress == null)
            .addAction(
                NotificationCompat.Action.Builder(
                    android.R.drawable.ic_menu_close_clear_cancel,
                    "Cancelar",
                    WorkManager.getInstance(applicationContext).createCancelPendingIntent(id),
                ).build(),
            )
            .build()

    private fun publishToDownloads(file: File, mediaType: String): Uri {
        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, file.name)
            put(
                MediaStore.MediaColumns.MIME_TYPE,
                if (mediaType == "audio") "audio/mpeg" else MimeTypeMap.getSingleton()
                    .getMimeTypeFromExtension(file.extension.lowercase()) ?: "application/octet-stream",
            )
            put(
                MediaStore.MediaColumns.RELATIVE_PATH,
                Environment.DIRECTORY_DOWNLOADS + "/SnapGrab",
            )
            put(MediaStore.MediaColumns.IS_PENDING, 1)
        }
        val resolver = applicationContext.contentResolver
        val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
            ?: error("Não foi possível criar o arquivo em Downloads/SnapGrab.")

        try {
            val destination = resolver.openOutputStream(uri, "w")
                ?: error("Não foi possível gravar o arquivo em Downloads/SnapGrab.")
            file.inputStream().use { input ->
                destination.use { output -> input.copyTo(output) }
            }
            val completed = ContentValues().apply {
                put(MediaStore.MediaColumns.IS_PENDING, 0)
            }
            check(resolver.update(uri, completed, null, null) == 1) {
                "Não foi possível concluir a gravação em Downloads/SnapGrab."
            }
            return uri
        } catch (error: Exception) {
            resolver.delete(uri, null, null)
            throw error
        }
    }

    companion object {
        const val KEY_URL = "url"
        const val KEY_MEDIA_TYPE = "media_type"
        const val KEY_QUALITY = "quality"
        const val KEY_PERCENT = "percent"
        const val KEY_STATUS = "status"
        const val KEY_ERROR = "error"
        const val KEY_URI = "uri"
        const val KEY_NAME = "name"

        private const val CHANNEL_ID = "snapgrab-downloads"
    }
}
