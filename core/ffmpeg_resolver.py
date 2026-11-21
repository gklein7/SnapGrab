import shutil
import os
import sys

def get_ffmpeg_path():
    """Retorna o caminho do executável ffmpeg (do PATH ou do pacote imageio_ffmpeg)."""
    # 1. Checa se ffmpeg já está no PATH do sistema
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg

    # 2. Tenta obter via imageio_ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(ffmpeg_exe):
            return ffmpeg_exe
    except Exception:
        pass

    # 3. Checa diretório local 'bin/ffmpeg.exe'
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_bin = os.path.join(base_dir, "bin", "ffmpeg.exe")
    if os.path.exists(local_bin):
        return local_bin

    return None


def get_ffprobe_path():
    """Retorna o caminho do executável ffprobe (do PATH ou ao lado do ffmpeg)."""
    sys_ffprobe = shutil.which("ffprobe")
    if sys_ffprobe:
        return sys_ffprobe

    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path:
        probe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
        sibling_probe = os.path.join(os.path.dirname(ffmpeg_path), probe_name)
        if os.path.exists(sibling_probe):
            return sibling_probe

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_bin = os.path.join(base_dir, "bin", "ffprobe.exe" if os.name == "nt" else "ffprobe")
    if os.path.exists(local_bin):
        return local_bin

    return None


if __name__ == "__main__":
    path = get_ffmpeg_path()
    print("FFmpeg encontrado em:", path)
    probe_path = get_ffprobe_path()
    print("FFprobe encontrado em:", probe_path)
