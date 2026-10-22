import os
import subprocess
from PIL import Image, ImageDraw
from config import AVAILABLE_QUALITIES, QUALITY_LABELS, get_download_dir

pystray = None
item = None


def _load_pystray():
    global pystray, item
    if pystray is None:
        import pystray as tray_module
        from pystray import MenuItem

        pystray = tray_module
        item = MenuItem


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
    def __init__(
        self, on_toggle_pause, on_download_clipboard, on_change_quality, on_quit,
        on_open_history=None, initial_quality="best"
    ):
        self.on_toggle_pause = on_toggle_pause
        self.on_download_clipboard = on_download_clipboard
        self.on_change_quality = on_change_quality
        self.on_quit = on_quit
        self.on_open_history = on_open_history
        self.current_quality = initial_quality
        self.is_monitoring = True
        self.icon = None

    def _select_quality(self, quality):
        def handler(icon, item):
            self.current_quality = quality
            if self.on_change_quality:
                self.on_change_quality(quality)
            if self.icon:
                self.icon.menu = self._get_menu()
        return handler

    def _get_quality_menu(self):
        _load_pystray()
        items = []
        for q in AVAILABLE_QUALITIES:
            label = QUALITY_LABELS.get(q, q)
            items.append(
                item(
                    label,
                    self._select_quality(q),
                    checked=lambda it, target_q=q: self.current_quality == target_q,
                    radio=True
                )
            )
        return pystray.Menu(*items)

    def _get_menu(self):
        _load_pystray()
        status_label = "🟢 Monitoramento: Ativo" if self.is_monitoring else "⏸️ Monitoramento: Pausado"
        toggle_label = "Pausar Monitoramento" if self.is_monitoring else "Retomar Monitoramento"
        q_label_current = QUALITY_LABELS.get(self.current_quality, self.current_quality)

        return pystray.Menu(
            item(status_label, lambda: None, enabled=False),
            item(toggle_label, self._toggle_monitoring),
            pystray.Menu.SEPARATOR,
            item("📥 Baixar Link do Clipboard", self._trigger_clipboard_download),
            item("📜 Histórico de Downloads", self._open_history),
            item(f"🎬 Resolução Padrão ({q_label_current})", self._get_quality_menu()),
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
            download_dir = get_download_dir()
            if hasattr(os, "startfile"):
                os.startfile(str(download_dir))
            else:
                subprocess.Popen(["xdg-open", str(download_dir)])
        except Exception as e:
            print("Erro ao abrir pasta:", e)

    def _open_history(self, icon, item):
        if self.on_open_history:
            self.on_open_history()

    def _quit(self, icon, item):
        self.icon.stop()
        if self.on_quit:
            self.on_quit()

    def set_quality(self, quality):
        """Atualiza externamente a qualidade selecionada."""
        self.current_quality = quality
        if self.icon:
            self.icon.menu = self._get_menu()

    def start(self):
        _load_pystray()
        image = create_tray_icon_image(True)
        self.icon = pystray.Icon(
            "media_downloader",
            image,
            "SnapGrab - Video & Audio Downloader",
            menu=self._get_menu()
        )
        self.icon.run_detached()

    def stop(self):
        if self.icon:
            self.icon.stop()
