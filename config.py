import json
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
APP_DATA_DIR = Path(
    os.environ.get("LOCALAPPDATA")
    or os.environ.get("APPDATA")
    or (Path.home() / ".snapgrab")
) / "SnapGrab"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = APP_DATA_DIR / "settings.json"
LEGACY_SETTINGS_FILE = BASE_DIR / "settings.json"

_DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads" / "Videos"
TOAST_TIMEOUT_SECONDS = 12
DEFAULT_VIDEO_QUALITY = "best"
COOKIE_BROWSER = "opera"
DEFAULT_MAX_CONCURRENT_DOWNLOADS = 2
DEFAULT_HISTORY_LIMIT = 100

SUPPORTED_DOMAINS = [
    "youtube.com", "youtu.be", "instagram.com", "twitter.com", "x.com",
    "tiktok.com", "threads.net", "facebook.com", "fb.watch", "reddit.com",
    "twitch.tv", "vimeo.com", "pinterest.com", "pin.it", "kwaicut.com",
    "kwai.com",
]

AVAILABLE_QUALITIES = ["best", "1080p", "720p", "480p"]
QUALITY_LABELS = {
    "best": "Máx (Melhor/4K)",
    "1080p": "1080p (Full HD)",
    "720p": "720p (HD)",
    "480p": "480p (Econômico)",
}


def load_settings():
    """Carrega configurações do perfil do usuário e migra o arquivo antigo."""
    settings = {
        "download_dir": str(_DEFAULT_DOWNLOAD_DIR),
        "video_quality": DEFAULT_VIDEO_QUALITY,
        "cookie_browser": COOKIE_BROWSER,
        "toast_timeout": TOAST_TIMEOUT_SECONDS,
        "max_concurrent_downloads": DEFAULT_MAX_CONCURRENT_DOWNLOADS,
    }
    source = SETTINGS_FILE if SETTINGS_FILE.exists() else LEGACY_SETTINGS_FILE
    if source.exists():
        try:
            with source.open("r", encoding="utf-8") as file:
                saved = json.load(file)
            if isinstance(saved, dict):
                settings.update(saved)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            print(f"Erro ao carregar configurações: {exc}")

    if settings.get("video_quality") not in AVAILABLE_QUALITIES:
        settings["video_quality"] = DEFAULT_VIDEO_QUALITY
    try:
        settings["toast_timeout"] = max(3, min(120, int(settings["toast_timeout"])))
    except (TypeError, ValueError):
        settings["toast_timeout"] = TOAST_TIMEOUT_SECONDS
    try:
        settings["max_concurrent_downloads"] = max(
            1, min(5, int(settings["max_concurrent_downloads"]))
        )
    except (TypeError, ValueError):
        settings["max_concurrent_downloads"] = DEFAULT_MAX_CONCURRENT_DOWNLOADS
    if not isinstance(settings.get("download_dir"), str) or not settings.get("download_dir"):
        settings["download_dir"] = str(_DEFAULT_DOWNLOAD_DIR)
    return settings


def save_settings(settings):
    """Salva configurações sem deixar um JSON parcialmente escrito."""
    try:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        temporary_file = SETTINGS_FILE.with_suffix(".tmp")
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(settings, file, indent=4, ensure_ascii=False)
        os.replace(temporary_file, SETTINGS_FILE)
        return True
    except OSError as exc:
        print(f"Erro ao salvar configurações: {exc}")
        return False


def get_current_quality():
    return load_settings()["video_quality"]


def set_current_quality(quality):
    if quality in AVAILABLE_QUALITIES:
        settings = load_settings()
        settings["video_quality"] = quality
        save_settings(settings)


def get_download_dir():
    settings = load_settings()
    path = Path(settings["download_dir"]).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def set_download_dir(path):
    settings = load_settings()
    settings["download_dir"] = str(Path(path).expanduser())
    save_settings(settings)


def get_cookie_browser():
    browser_name = load_settings().get("cookie_browser")
    return browser_name if isinstance(browser_name, str) and browser_name.strip() else COOKIE_BROWSER


def get_toast_timeout():
    return load_settings()["toast_timeout"]


def get_max_concurrent_downloads():
    return load_settings()["max_concurrent_downloads"]


# Compatibilidade com módulos que ainda importam estas constantes.
DEFAULT_DOWNLOAD_DIR = get_download_dir()
