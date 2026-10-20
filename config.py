import os
from pathlib import Path

# Diretório padrão para salvar os vídeos baixados
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads" / "Videos"
DEFAULT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Tempo (segundos) que o pop-up de notificação aguarda antes de sumir se ignorado
TOAST_TIMEOUT_SECONDS = 12

# Domínios suportados para interceptação automática no clipboard
SUPPORTED_DOMAINS = [
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "threads.net",
    "facebook.com",
    "fb.watch",
    "reddit.com",
    "twitch.tv",
    "vimeo.com",
    "pinterest.com",
    "pin.it",
    "kwaicut.com",
    "kwai.com"
]

# Navegador preferido para extração de cookies quando o site (ex: Instagram) exigir login
# Opções: 'chrome', 'edge', 'firefox', 'brave', 'opera', ou None
COOKIE_BROWSER = "chrome"
