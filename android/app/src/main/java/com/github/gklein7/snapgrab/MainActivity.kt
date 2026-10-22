package com.github.gklein7.snapgrab

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.work.WorkInfo
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage

class MainActivity : ComponentActivity() {
    private val viewModel: SnapGrabViewModel by viewModels()

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) {
        viewModel.startDownload()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        sharedText(intent)?.let(viewModel::setSharedText)
        setContent {
            val workInfo by viewModel.workInfo.collectAsStateWithLifecycle()
            MaterialTheme(
                colorScheme = lightColorScheme(
                    primary = androidx.compose.ui.graphics.Color(0xFF3659D9),
                    secondary = androidx.compose.ui.graphics.Color(0xFF55627A),
                ),
            ) {
                SnapGrabScreen(
                    viewModel = viewModel,
                    workInfo = workInfo,
                    onStartDownload = ::startDownload,
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        sharedText(intent)?.let(viewModel::setSharedText)
    }

    private fun startDownload() {
        if (
            Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        } else {
            viewModel.startDownload()
        }
    }

    private fun sharedText(intent: Intent?): String? =
        if (intent?.action == Intent.ACTION_SEND && intent.type == "text/plain") {
            intent.getCharSequenceExtra(Intent.EXTRA_TEXT)?.toString()
        } else {
            null
        }
}

@Composable
private fun SnapGrabScreen(
    viewModel: SnapGrabViewModel,
    workInfo: WorkInfo?,
    onStartDownload: () -> Unit,
) {
    val state = viewModel.uiState
    val context = LocalContext.current
    val uriHandler = LocalUriHandler.current
    val clipboard = context.getSystemService(ClipboardManager::class.java)
    var qualityMenuOpen by remember { mutableStateOf(false) }
    val active = state.isStartingDownload || workInfo?.state?.isFinished == false

    Surface(
        modifier = Modifier.fillMaxSize().safeDrawingPadding(),
        color = MaterialTheme.colorScheme.background,
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text("SnapGrab", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            Text("Baixe vídeos e áudio direto no seu Android.")

            OutlinedTextField(
                value = state.url,
                onValueChange = viewModel::updateUrl,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Link do vídeo") },
                placeholder = { Text("https://…") },
                minLines = 2,
                maxLines = 4,
            )

            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedButton(
                    onClick = {
                        val clip: ClipData? = clipboard?.primaryClip
                        val text = clip?.takeIf { it.itemCount > 0 }
                            ?.getItemAt(0)
                            ?.coerceToText(context)
                            ?.toString()
                        viewModel.setSharedText(text)
                    },
                ) {
                    Text("Colar link")
                }
                Button(
                    onClick = viewModel::lookup,
                    enabled = !state.isLookingUp && state.url.isNotBlank(),
                ) {
                    if (state.isLookingUp) {
                        CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                    } else {
                        Text("Buscar prévia")
                    }
                }
            }

            state.errorMessage?.let {
                Text(it, color = MaterialTheme.colorScheme.error)
            }

            state.preview?.let { preview ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        if (!preview.thumbnail.isNullOrBlank()) {
                            AsyncImage(
                                model = preview.thumbnail,
                                contentDescription = "Miniatura do vídeo",
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(190.dp),
                                contentScale = ContentScale.Crop,
                            )
                        }
                        Text(preview.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        if (preview.uploader.isNotBlank()) {
                            Text(preview.uploader, style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }

            Text("Formato", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                FilterChip(
                    selected = state.mediaType == "video",
                    onClick = { viewModel.setMediaType("video") },
                    label = { Text("Vídeo") },
                )
                FilterChip(
                    selected = state.mediaType == "audio",
                    onClick = { viewModel.setMediaType("audio") },
                    label = { Text("Áudio MP3") },
                )
            }

            if (state.mediaType == "video") {
                Box {
                    OutlinedButton(onClick = { qualityMenuOpen = true }) {
                        val selected = state.preview?.qualityOptions
                            ?.firstOrNull { it.value == state.quality }?.label ?: "Máx."
                        Text("Qualidade: $selected")
                    }
                    DropdownMenu(
                        expanded = qualityMenuOpen,
                        onDismissRequest = { qualityMenuOpen = false },
                    ) {
                        (state.preview?.qualityOptions ?: listOf(QualityOption("best", "Máx.")))
                            .forEach { option ->
                                DropdownMenuItem(
                                    text = { Text(option.label) },
                                    onClick = {
                                        viewModel.selectQuality(option.value)
                                        qualityMenuOpen = false
                                    },
                                )
                            }
                    }
                }
            }

            Button(
                onClick = onStartDownload,
                enabled = !active && state.url.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (active) "Download em andamento" else "Baixar")
            }

            if (active || workInfo?.state == WorkInfo.State.SUCCEEDED) {
                DownloadStatus(workInfo, active, onCancel = viewModel::cancelDownload)
            }

            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "github.com/gklein7",
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .clickable {
                        uriHandler.openUri("https://github.com/gklein7")
                    },
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun DownloadStatus(
    workInfo: WorkInfo?,
    active: Boolean,
    onCancel: () -> Unit,
) {
    val percent = workInfo?.progress?.getInt(DownloadWorker.KEY_PERCENT, 0) ?: 0
    val status = workInfo?.progress?.getString(DownloadWorker.KEY_STATUS)
    val message = when {
        workInfo == null -> "Preparando download…"
        workInfo.state == WorkInfo.State.SUCCEEDED -> "Concluído — salvo em Downloads/SnapGrab."
        workInfo.state == WorkInfo.State.FAILED ->
            workInfo.outputData.getString(DownloadWorker.KEY_ERROR) ?: "O download falhou."
        workInfo.state == WorkInfo.State.CANCELLED -> "Download cancelado."
        workInfo.state == WorkInfo.State.ENQUEUED -> "Na fila para iniciar…"
        workInfo.state == WorkInfo.State.BLOCKED -> "Aguardando…"
        else -> status ?: "Baixando…"
    }

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(message, style = MaterialTheme.typography.bodyMedium)
        if (active) {
            LinearProgressIndicator(
                progress = { percent.coerceIn(0, 100) / 100f },
                modifier = Modifier.fillMaxWidth(),
            )
            TextButton(onClick = onCancel, modifier = Modifier.align(Alignment.End)) {
                Text("Cancelar")
            }
        }
    }
}
