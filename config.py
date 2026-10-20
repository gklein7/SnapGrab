import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "settings.json"

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
COOKIE_BROWSER = "chrome"

# Qualidades disponíveis para download de vídeo
AVAILABLE_QUALITIES = ["best", "1080p", "720p", "480p"]
QUALITY_LABELS = {
    "best": "Máx (Melhor/4K)",
    "1080p": "1080p (Full HD)",
    "720p": "720p (HD)",
    "480p": "480p (Econômico)"
}

# Qualidade padrão inicial
DEFAULT_VIDEO_QUALITY = "best"

def load_settings():
    """Carrega as configurações salvas em settings.json ou retorna os padrões."""
    settings = {
        "download_dir": str(DEFAULT_DOWNLOAD_DIR),
        "video_quality": DEFAULT_VIDEO_QUALITY,
        "cookie_browser": COOKIE_BROWSER,
        "toast_timeout": TOAST_TIMEOUT_SECONDS
    }
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                settings.update(saved)
        except Exception as e:
            print("Erro ao carregar settings.json:", e)
    return settings

def save_settings(settings):
    """Salva as configurações atualizadas em settings.json."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("Erro ao salvar settings.json:", e)

def get_current_quality():
    """Retorna a qualidade padrão salva."""
    settings = load_settings()
    return settings.get("video_quality", DEFAULT_VIDEO_QUALITY)

def set_current_quality(quality):
    """Atualiza e salva a qualidade padrão."""
    if quality in AVAILABLE_QUALITIES:
        settings = load_settings()
        settings["video_quality"] = quality
        save_settings(settings)
