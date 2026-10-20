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

if __name__ == "__main__":
    path = get_ffmpeg_path()
    print("FFmpeg encontrado em:", path)
