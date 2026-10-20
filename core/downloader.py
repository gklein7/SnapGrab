import os
import sys
from pathlib import Path
import yt_dlp
from config import DEFAULT_DOWNLOAD_DIR, COOKIE_BROWSER
from core.ffmpeg_resolver import get_ffmpeg_path

class MediaDownloader:
    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir) if output_dir else DEFAULT_DOWNLOAD_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_path = get_ffmpeg_path()

    def get_info(self, url):
        """Obtém informações rápidas do vídeo (título, autor, miniatura, duração)."""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = self.ffmpeg_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Vídeo sem título'),
                    'uploader': info.get('uploader') or info.get('channel', 'Desconhecido'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail'),
                    'url': url
                }
        except Exception as e:
            # Fallback amigável se info rápida falhar
            return {
                'title': url,
                'uploader': '',
                'duration': 0,
                'thumbnail': None,
                'url': url,
                'error': str(e)
            }

    def download(self, url, media_type="video", progress_callback=None, use_cookies=False, browser_name=COOKIE_BROWSER):
        """
        Baixa o vídeo ou áudio do link fornecido.
        :param url: URL do YouTube, Instagram, X, TikTok, etc.
        :param media_type: 'video' (MP4 1080p/Max) ou 'audio' (MP3 320kbps)
        :param progress_callback: Função chamada com dict de status (percent, speed, eta, status, filename)
        :param use_cookies: Se deve tentar extrair cookies do navegador
        :param browser_name: Navegador para cookies ('chrome', 'edge', etc.)
        """
        def ydl_hook(d):
            if not progress_callback:
                return

            status = d.get('status')
            if status == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                speed = d.get('speed') or 0 # bytes/s
                eta = d.get('eta') or 0 # segundos
                percent = (downloaded / total_bytes * 100) if total_bytes > 0 else 0

                speed_mb = speed / (1024 * 1024) if speed else 0

                progress_callback({
                    'status': 'downloading',
                    'percent': percent,
                    'speed_str': f"{speed_mb:.1f} MB/s" if speed_mb >= 0.1 else f"{speed/1024:.0f} KB/s",
                    'eta_str': f"{eta}s" if eta else "--",
                    'filename': d.get('filename', '')
                })
            elif status == 'finished':
                progress_callback({
                    'status': 'processing',
                    'percent': 100,
                    'speed_str': '',
                    'eta_str': '',
                    'filename': d.get('filename', '')
                })

        out_template = str(self.output_dir / '%(title).120s [%(id)s].%(ext)s')

        ydl_opts = {
            'outtmpl': out_template,
            'progress_hooks': [ydl_hook],
            'quiet': True,
            'no_warnings': True,
        }

        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = self.ffmpeg_path

        if use_cookies and browser_name:
            ydl_opts['cookiesfrombrowser'] = (browser_name,)

        if media_type == 'audio':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }]
            })
        else: # video
            ydl_opts.update({
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
                'merge_output_format': 'mp4'
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                target_filename = ydl.prepare_filename(info)
                if media_type == 'audio':
                    target_filename = os.path.splitext(target_filename)[0] + '.mp3'
                elif not target_filename.endswith('.mp4'):
                    target_filename = os.path.splitext(target_filename)[0] + '.mp4'

                if progress_callback:
                    progress_callback({
                        'status': 'completed',
                        'percent': 100,
                        'filename': target_filename,
                        'title': info.get('title', 'Vídeo')
                    })
                return {'success': True, 'filename': target_filename, 'title': info.get('title')}

        except Exception as e:
            err_msg = str(e)
            # Se falhou por autenticação/restrição (comum no Instagram) e não tentou cookies ainda, tenta com cookies
            if not use_cookies and browser_name and any(k in err_msg.lower() for k in ['login', 'sign in', 'authenticate', 'rate limit', 'private']):
                print(f"Tentando novamente com cookies do {browser_name}...")
                return self.download(url, media_type, progress_callback, use_cookies=True, browser_name=browser_name)

            if progress_callback:
                progress_callback({
                    'status': 'error',
                    'error': err_msg
                })
            return {'success': False, 'error': err_msg}

if __name__ == "__main__":
    # Teste rápido
    downloader = MediaDownloader()
    print("Módulo MediaDownloader pronto.")
