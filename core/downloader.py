import os
from pathlib import Path
import yt_dlp
from config import get_cookie_browser, get_download_dir
from core.ffmpeg_resolver import get_ffmpeg_path

def get_browser_cookie_spec(browser_name):
    """
    Resolve a tupla de navegador/perfil para o yt-dlp.
    Detecta automaticamente Opera padrão e Opera GX no Windows.
    """
    if not browser_name:
        return None
    b = browser_name.lower().strip()
    appdata = os.environ.get("APPDATA", "")
    if b in ("opera", "operagx"):
        gx_path = os.path.join(appdata, "Opera Software", "Opera GX Stable")
        stable_path = os.path.join(appdata, "Opera Software", "Opera Stable")
        if b == "operagx" or (not os.path.exists(stable_path) and os.path.exists(gx_path)):
            return ("opera", gx_path)
        return ("opera",)
    return (b,)

class MediaDownloader:
    def __init__(self, output_dir=None, ffmpeg_path=None):
        self.output_dir = Path(output_dir) if output_dir else get_download_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_path = ffmpeg_path if ffmpeg_path is not None else get_ffmpeg_path()

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
                preview = self._build_preview_details(info)
                return {
                    'title': info.get('title', 'Vídeo sem título'),
                    'uploader': info.get('uploader') or info.get('channel', 'Desconhecido'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail'),
                    'url': url,
                    **preview,
                }
        except Exception as e:
            # Fallback amigável se info rápida falhar
            return {
                'title': url,
                'uploader': '',
                'duration': 0,
                'thumbnail': None,
                'url': url,
                'available_resolutions': [],
                'quality_options': [{'value': 'best', 'label': 'Máx.'}],
                'size_estimates': {'best': 0},
                'audio_size_estimate': 0,
                'error': str(e)
            }

    @staticmethod
    def _format_size_estimate(format_info, duration):
        """Estima o tamanho de um formato usando bytes ou bitrate e duração."""
        for key in ('filesize', 'filesize_approx'):
            try:
                size = int(format_info.get(key) or 0)
            except (TypeError, ValueError):
                size = 0
            if size > 0:
                return size

        try:
            bitrate_kbps = float(format_info.get('tbr') or format_info.get('abr') or 0)
            duration_seconds = float(duration or 0)
        except (TypeError, ValueError):
            return 0
        if bitrate_kbps <= 0 or duration_seconds <= 0:
            return 0
        # kb/s * segundos * 1000 bits / 8 bits por byte.
        return int(duration_seconds * bitrate_kbps * 125)

    @classmethod
    def _estimate_video_size(cls, formats, duration, max_height=None):
        video_formats = []
        audio_formats = []
        combined_formats = []
        for format_info in formats:
            if not isinstance(format_info, dict):
                continue
            video_codec = format_info.get('vcodec')
            audio_codec = format_info.get('acodec')
            has_video = video_codec not in (None, 'none')
            has_audio = audio_codec not in (None, 'none')
            if has_video:
                try:
                    height = int(format_info.get('height') or 0)
                except (TypeError, ValueError):
                    continue
                if height <= 0 or (max_height and height > max_height):
                    continue
                if has_audio:
                    combined_formats.append(format_info)
                else:
                    video_formats.append(format_info)
            elif has_audio:
                audio_formats.append(format_info)

        def rank(format_info):
            try:
                height = int(format_info.get('height') or 0)
                bitrate = float(format_info.get('tbr') or format_info.get('abr') or 0)
            except (TypeError, ValueError):
                height = 0
                bitrate = 0
            return (
                height,
                bitrate,
                cls._format_size_estimate(format_info, duration),
            )

        if video_formats and audio_formats:
            best_video = max(video_formats, key=rank)
            best_audio = max(audio_formats, key=rank)
            video_size = cls._format_size_estimate(best_video, duration)
            audio_size = cls._format_size_estimate(best_audio, duration)
            if video_size and audio_size:
                return video_size + audio_size

        if combined_formats:
            return cls._format_size_estimate(max(combined_formats, key=rank), duration)
        return 0

    @classmethod
    def _build_preview_details(cls, info):
        """Constrói resoluções reais e estimativas para a prévia do pop-up."""
        duration = info.get('duration') or 0
        formats = info.get('formats') or []
        heights = set()
        for format_info in formats:
            if not isinstance(format_info, dict):
                continue
            if format_info.get('vcodec') in (None, 'none'):
                continue
            try:
                height = int(format_info.get('height') or 0)
            except (TypeError, ValueError):
                continue
            if height > 0:
                heights.add(height)

        available_heights = sorted(heights, reverse=True)
        max_height = available_heights[0] if available_heights else None
        quality_options = [{'value': 'best', 'label': f'Máx. · {max_height}p' if max_height else 'Máx.'}]
        # Cada resolução encontrada fica disponível para seleção no pop-up.
        for height in [value for value in available_heights if value != max_height]:
            quality_options.append({'value': f'{height}p', 'label': f'{height}p'})

        size_estimates = {
            'best': cls._estimate_video_size(formats, duration),
        }
        for option in quality_options[1:]:
            height = int(option['value'][:-1])
            size_estimates[option['value']] = cls._estimate_video_size(
                formats, duration, max_height=height
            )

        audio_size_estimate = 0
        try:
            duration_seconds = float(duration or 0)
            if duration_seconds > 0:
                # O áudio é convertido para MP3 a 320 kb/s pelo downloader.
                audio_size_estimate = int(duration_seconds * 320 * 125)
        except (TypeError, ValueError):
            pass

        return {
            'available_resolutions': available_heights,
            'quality_options': quality_options,
            'size_estimates': size_estimates,
            'audio_size_estimate': audio_size_estimate,
        }

    def download(
        self, url, media_type="video", quality="best", progress_callback=None,
        use_cookies=False, browser_name=None, cancel_event=None, allow_cookie_retry=True
    ):
        """
        Baixa o vídeo ou áudio do link fornecido.
        :param url: URL do YouTube, Instagram, X, TikTok, etc.
        :param media_type: 'video' ou 'audio'
        :param quality: Resolução desejada ('best', '1080p', '720p', '480p')
        :param progress_callback: Função chamada com dict de status (percent, speed, eta, status, filename)
        :param use_cookies: Se deve tentar extrair cookies do navegador
        :param browser_name: Navegador para cookies ('chrome', 'edge', etc.)
        :param cancel_event: Evento opcional para interromper um download em andamento.
        :param allow_cookie_retry: Permite a tentativa automática de cookies do navegador.
        """
        browser_name = browser_name or get_cookie_browser()

        def check_cancelled(_data=None):
            if cancel_event is not None and cancel_event.is_set():
                raise yt_dlp.utils.DownloadCancelled("Download cancelado pelo usuário.")

        def ydl_hook(d):
            check_cancelled(d)
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
            'postprocessor_hooks': [check_cancelled],
            'quiet': True,
            'no_warnings': True,
        }

        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = self.ffmpeg_path

        # Suporte a arquivo cookies.txt na raiz do projeto ou extração direta do navegador
        local_cookies_file = Path(__file__).resolve().parent.parent / "cookies.txt"
        if local_cookies_file.exists():
            ydl_opts['cookiefile'] = str(local_cookies_file)
        elif use_cookies and browser_name:
            cookie_spec = get_browser_cookie_spec(browser_name)
            if cookie_spec:
                ydl_opts['cookiesfrombrowser'] = cookie_spec

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
            if not quality or quality == 'best':
                fmt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
            else:
                h = quality.lower().replace('p', '')
                fmt = f'bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={h}]+bestaudio/best[height<={h}]/best'

            ydl_opts.update({
                'format': fmt,
                'merge_output_format': 'mp4'
            })

        try:
            check_cancelled()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                target_filename = self._resolve_output_path(ydl, info, media_type)

                if progress_callback:
                    progress_callback({
                        'status': 'completed',
                        'percent': 100,
                        'filename': target_filename,
                        'title': info.get('title', 'Vídeo'),
                        'quality': quality if media_type == 'video' else 'mp3'
                    })
                return {
                    'success': True,
                    'filename': target_filename,
                    'title': info.get('title'),
                    'quality': quality if media_type == 'video' else 'mp3'
                }

        except Exception as e:
            err_msg = str(e)
            if isinstance(e, yt_dlp.utils.DownloadCancelled) or (
                cancel_event is not None and cancel_event.is_set()
            ):
                if progress_callback:
                    progress_callback({'status': 'cancelled', 'error': 'Download cancelado.'})
                return {'success': False, 'cancelled': True, 'error': 'Download cancelado.'}

            # Se falhou por autenticação/restrição (comum no Instagram) e não tentou cookies ainda, tenta com cookies
            if allow_cookie_retry and not use_cookies and browser_name and any(k in err_msg.lower() for k in ['login', 'sign in', 'authenticate', 'rate limit', 'private']):
                print(f"Tentando novamente com cookies do {browser_name}...")
                return self.download(
                    url,
                    media_type,
                    quality,
                    progress_callback,
                    use_cookies=True,
                    browser_name=browser_name,
                    cancel_event=cancel_event,
                    allow_cookie_retry=allow_cookie_retry,
                )

            if use_cookies and any(k in err_msg.lower() for k in ['could not copy', 'database is locked', 'permission denied', 'errno 13', 'sharing violation']):
                b_name = "Opera / Opera GX" if "opera" in str(browser_name).lower() else browser_name.title()
                err_msg = f"Feche o {b_name} para liberar o acesso aos cookies ou adicione um cookies.txt"

            err_msg = self._explain_error(err_msg)
            if progress_callback:
                progress_callback({
                    'status': 'error',
                    'error': err_msg
                })
            return {'success': False, 'error': err_msg}

    def _resolve_output_path(self, ydl, info, media_type):
        """Usa o caminho que o yt-dlp realmente produziu após merge/conversão."""
        candidates = []
        if info.get('filepath'):
            candidates.append(Path(info['filepath']))

        try:
            prepared_filename = Path(ydl.prepare_filename(info))
            expected_suffix = '.mp3' if media_type == 'audio' else '.mp4'
            candidates.extend(
                [prepared_filename.with_suffix(expected_suffix), prepared_filename]
            )
        except Exception:
            prepared_filename = None

        if info.get('_filename'):
            source_filename = Path(info['_filename'])
            expected_suffix = '.mp3' if media_type == 'audio' else '.mp4'
            candidates.extend(
                [source_filename.with_suffix(expected_suffix), source_filename]
            )

        # requested_downloads lista os fluxos temporários individuais; só use como
        # fallback, depois do nome final calculado pelo yt-dlp.
        for requested in info.get('requested_downloads') or []:
            if requested.get('filepath'):
                candidates.append(Path(requested['filepath']))

        seen = set()
        for candidate in candidates:
            candidate = candidate.expanduser()
            key = str(candidate)
            if key in seen:
                continue
            seen.add(key)
            if candidate.is_file():
                return str(candidate)

        # Não inventa uma extensão quando o extractor não informa o arquivo final.
        return str(candidates[0]) if candidates else str(self.output_dir)

    def _explain_error(self, error):
        """Acrescenta uma indicação prática aos erros mais comuns do yt-dlp."""
        message = str(error)
        lowered = message.lower()
        if "ffmpeg" in lowered and not self.ffmpeg_path:
            return "FFmpeg não encontrado. Reinstale as dependências do SnapGrab.\n" + message
        if any(term in lowered for term in ("login", "sign in", "authenticate", "private", "members-only")):
            return "O conteúdo exige login ou não está público. Configure cookies do navegador e tente novamente.\n" + message
        if "requested format" in lowered or "format is not available" in lowered:
            return "A qualidade pedida não está disponível para este link. Tente outra resolução.\n" + message
        if "unsupported url" in lowered:
            return "Este link não é compatível com a versão atual do yt-dlp. Atualize o motor e tente novamente.\n" + message
        if any(term in lowered for term in ("timed out", "connection reset", "network is unreachable", "temporary failure")):
            return "Falha temporária de conexão. Verifique a internet e tente novamente.\n" + message
        return message

if __name__ == "__main__":
    downloader = MediaDownloader()
    print("Módulo MediaDownloader pronto.")
