import sys
import os
import threading
import pyperclip
from config import DEFAULT_DOWNLOAD_DIR, get_current_quality, set_current_quality, QUALITY_LABELS
from core.downloader import MediaDownloader
from clipboard_watcher import ClipboardWatcher
from ui.toast import ToastManager
from ui.tray import SystemTrayApp

class QuickDownloaderApp:
    def __init__(self):
        self.current_quality = get_current_quality()
        self.downloader = MediaDownloader()
        self.toast_mgr = ToastManager(self.handle_download_request)
        self.watcher = ClipboardWatcher(self.handle_url_detected)
        self.tray = SystemTrayApp(
            on_toggle_pause=self.handle_toggle_pause,
            on_download_clipboard=self.handle_manual_clipboard_download,
            on_change_quality=self.handle_change_quality,
            on_quit=self.quit,
            initial_quality=self.current_quality
        )

    def handle_change_quality(self, new_quality):
        """Atualiza a resolução padrão global e persiste nas configurações."""
        self.current_quality = new_quality
        set_current_quality(new_quality)
        label = QUALITY_LABELS.get(new_quality, new_quality)
        print(f"[Configuração] Resolução padrão alterada para: {label}")

    def handle_url_detected(self, url):
        """Disparado quando um link suportado é copiado para a área de transferência."""
        print(f"[Detectado] Link: {url}")
        # Obtém título e metadados rápidos em segundo plano
        info = self.downloader.get_info(url)
        # Exibe o toast visual passando a qualidade atual configurada
        self.toast_mgr.show_toast(url, info, quality=self.current_quality)

    def handle_download_request(self, url, media_type, quality, toast):
        """Disparado quando o usuário clica em Baixar Vídeo ou Baixar Áudio no Toast."""
        def run_dl():
            q_label = quality if media_type == "video" else "mp3"
            print(f"[Download Iniciado] Tipo: {media_type} | Qualidade: {q_label} | URL: {url}")
            self.downloader.download(
                url=url,
                media_type=media_type,
                quality=quality,
                progress_callback=lambda data: self.toast_mgr.update_progress(toast, data)
            )

        threading.Thread(target=run_dl, daemon=True).start()

    def handle_toggle_pause(self, is_monitoring):
        if is_monitoring:
            self.watcher.resume()
            print("[Status] Monitoramento retomado.")
        else:
            self.watcher.pause()
            print("[Status] Monitoramento pausado.")

    def handle_manual_clipboard_download(self):
        """Força a verificação do clipboard via menu da bandeja."""
        try:
            curr = pyperclip.paste().strip()
            if self.watcher.is_supported_url(curr):
                threading.Thread(target=self.handle_url_detected, args=(curr,), daemon=True).start()
            else:
                print("[Aviso] O link atual na área de transferência não é suportado:", curr)
        except Exception as e:
            print("Erro ao ler clipboard:", e)

    def start(self):
        q_label = QUALITY_LABELS.get(self.current_quality, self.current_quality)
        print("=" * 60)
        print("🚀 SnapGrab - Fast Video & Audio Downloader Iniciado!")
        print(f"📁 Pasta de destino: {DEFAULT_DOWNLOAD_DIR}")
        print(f"🎬 Resolução padrão atual: {q_label}")
        print("🟢 Monitorando área de transferência para links de:")
        print("   YouTube, Instagram, X (Twitter), TikTok, Reddit, etc.")
        print("=" * 60)

        # Inicia monitor de clipboard
        self.watcher.start()

        # Inicia ícone da bandeja
        self.tray.start()

        # Roda o loop principal da interface gráfica (Tkinter)
        self.toast_mgr.run()

    def quit(self):
        print("Encerrando aplicativo...")
        self.watcher.stop()
        self.tray.stop()
        self.toast_mgr.stop()
        sys.exit(0)

def direct_cli_download(url, media_type="video", quality="best"):
    """Permite uso direto via linha de comando se passado argumento: python main.py <url> [video|audio] [quality]"""
    downloader = MediaDownloader()
    q_label = quality if media_type == "video" else "mp3"
    print(f"Baixando diretamente: {url} ({media_type} - {q_label})...")

    def cli_progress(data):
        st = data.get("status")
        if st == "downloading":
            pct = data.get("percent", 0)
            spd = data.get("speed_str", "")
            eta = data.get("eta_str", "")
            sys.stdout.write(f"\rBaixando: {pct:.1f}% | Vel: {spd} | ETA: {eta}  ")
            sys.stdout.flush()
        elif st == "processing":
            sys.stdout.write("\rProcessando com FFmpeg...                    \n")
            sys.stdout.flush()
        elif st == "completed":
            print(f"\n✅ Concluído! Salvo em: {data.get('filename')}")
        elif st == "error":
            print(f"\n❌ Erro: {data.get('error')}")

    res = downloader.download(url, media_type=media_type, quality=quality, progress_callback=cli_progress)
    return res

def main():
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        # Modo CLI direto: python main.py <url> [video|audio] [quality]
        url = sys.argv[1]
        media_type = sys.argv[2] if len(sys.argv) > 2 else "video"
        quality = sys.argv[3] if len(sys.argv) > 3 else get_current_quality()
        direct_cli_download(url, media_type, quality)
    else:
        # Modo App com Monitor de Bandeja
        app = QuickDownloaderApp()
        app.start()

if __name__ == "__main__":
    main()
