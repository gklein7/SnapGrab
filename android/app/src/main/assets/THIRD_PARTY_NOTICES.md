# Avisos de terceiros do SnapGrab para Android

O SnapGrab é distribuído sob a licença MIT. O arquivo `LICENSE` está na raiz do repositório e também é incluído no pacote de fontes de FFmpeg.

## Runtime Python e yt-dlp

Chaquopy 17.1.0 é distribuído sob MIT; o runtime Python segue a licença PSF. O yt-dlp é distribuído sob Unlicense. Consulte os projetos e licenças em [Chaquopy](https://chaquo.com/chaquopy/license/), [Python](https://docs.python.org/3/license.html) e [licença do yt-dlp](https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE).

## FFmpeg 8.1.3

O FFmpeg é compilado para `arm64-v8a` com suporte a libmp3lame, sem habilitar componentes GPL ou não livres. O código-fonte correspondente, incluindo a configuração de build, é publicado junto ao APK como `SnapGrab-FFmpeg-Source.tar.gz` na mesma GitHub Release. O script de build registra as versões e valida os hashes SHA-256 dos arquivos-fonte.

O FFmpeg é licenciado sob LGPL 2.1 ou posterior nas opções de build usadas. Código-fonte: [ffmpeg.org](https://ffmpeg.org/). Licenciamento: [ffmpeg.org/legal.html](https://ffmpeg.org/legal.html).

## LAME 3.100

A biblioteca libmp3lame é compilada estaticamente no FFmpeg para conversão MP3 e é distribuída sob LGPL 2.0 ou posterior. O código-fonte e o arquivo de licença estão incluídos no pacote de fontes acima. Código-fonte: [lame.sourceforge.io](https://lame.sourceforge.io/).
