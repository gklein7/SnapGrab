import time
import threading
import urllib.parse
import pyperclip
from config import SUPPORTED_DOMAINS

class ClipboardWatcher:
    def __init__(self, on_url_detected):
        self.on_url_detected = on_url_detected
        self.last_clipboard_text = None
        self.is_running = False
        self.is_paused = False
        self.thread = None

    def is_supported_url(self, text):
        if not text or not isinstance(text, str):
            return False
        text = text.strip()
        try:
            parsed = urllib.parse.urlparse(text)
            if parsed.scheme.lower() not in {"http", "https"}:
                return False
            hostname = (parsed.hostname or "").lower().rstrip(".")
            if not hostname:
                return False
            for domain in SUPPORTED_DOMAINS:
                domain = domain.lower().lstrip(".")
                if hostname == domain or hostname.endswith("." + domain):
                    return True
        except Exception:
            return False

        return False

    def process_clipboard_text(self, text):
        """Processa cada mudança do clipboard, inclusive texto que não é URL."""
        current_text = text.strip() if isinstance(text, str) else ""
        if current_text == self.last_clipboard_text:
            return False
        self.last_clipboard_text = current_text
        if not self.is_supported_url(current_text):
            return False
        threading.Thread(
            target=self.on_url_detected,
            args=(current_text,),
            daemon=True,
        ).start()
        return True

    def _loop(self):
        while self.is_running:
            if not self.is_paused:
                try:
                    self.process_clipboard_text(pyperclip.paste())
                except Exception as e:
                    # Clipboard pode estar temporariamente bloqueado por outro app
                    pass

            time.sleep(0.8)

    def start(self):
        if not self.is_running:
            self.is_running = True
            # Evita disparar um link que já estava copiado quando o app foi aberto.
            try:
                self.last_clipboard_text = pyperclip.paste().strip()
            except Exception:
                pass

            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.is_running = False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False
