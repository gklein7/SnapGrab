import os
import subprocess
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
from config import DEFAULT_DOWNLOAD_DIR

def create_tray_icon_image(active=True):
    """Cria dinamicamente uma imagem moderna para o ícone de bandeja."""
    size = (64, 64)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Círculo de fundo
    bg_color = (37, 99, 235, 255) if active else (100, 116, 139, 255) # Azul ou cinza
    draw.ellipse([4, 4, 60, 60], fill=bg_color)

    # Seta de download desenhada
    arrow_color = (255, 255, 255, 255)
    # Haste da seta
    draw.rectangle([28, 16, 36, 36], fill=arrow_color)
    # Ponta da seta (triângulo)
    draw.polygon([(20, 36), (44, 36), (32, 48)], fill=arrow_color)
    # Barra da base
    draw.rectangle([20, 50, 44, 54], fill=arrow_color)

    return image

class SystemTrayApp:
    def __init__(self, on_toggle_pause, on_download_clipboard, on_quit):
        self.on_toggle_pause = on_toggle_pause
        self.on_download_clipboard = on_download_clipboard
        self.on_quit = on_quit
        self.is_monitoring = True
        self.icon = None

    def _get_menu(self):
        status_label = "🟢 Monitoramento: Ativo" if self.is_monitoring else "⏸️ Monitoramento: Pausado"
        toggle_label = "Pausar Monitoramento" if self.is_monitoring else "Retomar Monitoramento"

        return pystray.Menu(
            item(status_label, lambda: None, enabled=False),
            item(toggle_label, self._toggle_monitoring),
            pystray.Menu.SEPARATOR,
            item("📥 Baixar Link do Clipboard", self._trigger_clipboard_download),
            item("📂 Abrir Pasta de Vídeos", self._open_downloads_folder),
            pystray.Menu.SEPARATOR,
            item("❌ Sair", self._quit)
        )

    def _toggle_monitoring(self, icon, item):
        self.is_monitoring = not self.is_monitoring
        self.on_toggle_pause(self.is_monitoring)
        self.icon.icon = create_tray_icon_image(self.is_monitoring)
        self.icon.menu = self._get_menu()

    def _trigger_clipboard_download(self, icon, item):
        if self.on_download_clipboard:
            self.on_download_clipboard()

    def _open_downloads_folder(self, icon, item):
        try:
            os.startfile(str(DEFAULT_DOWNLOAD_DIR))
        except Exception as e:
            print("Erro ao abrir pasta:", e)

    def _quit(self, icon, item):
        self.icon.stop()
        if self.on_quit:
            self.on_quit()

    def start(self):
        image = create_tray_icon_image(True)
        self.icon = pystray.Icon(
            "media_downloader",
            image,
            "Video & Audio Quick Downloader",
            menu=self._get_menu()
        )
        self.icon.run_detached()

    def stop(self):
        if self.icon:
            self.icon.stop()
