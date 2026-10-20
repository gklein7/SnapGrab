import time
import threading
import urllib.parse
import pyperclip
from config import SUPPORTED_DOMAINS

class ClipboardWatcher:
    def __init__(self, on_url_detected):
        self.on_url_detected = on_url_detected
        self.last_url = ""
        self.is_running = False
        self.is_paused = False
        self.thread = None

    def is_supported_url(self, text):
        if not text or not isinstance(text, str):
            return False
        text = text.strip()
        if not (text.startswith("http://") or text.startswith("https://")):
            return False

        try:
            parsed = urllib.parse.urlparse(text)
            netloc = parsed.netloc.lower()
            # Remove porta se houver
            netloc = netloc.split(":")[0]

            for domain in SUPPORTED_DOMAINS:
                if domain in netloc:
                    return True
        except Exception:
            return False

        return False

    def _loop(self):
        while self.is_running:
            if not self.is_paused:
                try:
                    current_text = pyperclip.paste()
                    if current_text:
                        current_text = current_text.strip()
                        if current_text != self.last_url and self.is_supported_url(current_text):
                            self.last_url = current_text
                            # Dispara o callback em uma thread separada para não travar o loop
                            threading.Thread(
                                target=self.on_url_detected,
                                args=(current_text,),
                                daemon=True
                            ).start()
                except Exception as e:
                    # Clipboard pode estar temporariamente bloqueado por outro app
                    pass

            time.sleep(0.8)

    def start(self):
        if not self.is_running:
            self.is_running = True
            # Inicializa last_url com o que já estiver no clipboard para não disparar logo ao ligar
            try:
                curr = pyperclip.paste().strip()
                if self.is_supported_url(curr):
                    self.last_url = curr
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
