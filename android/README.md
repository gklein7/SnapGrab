# SnapGrab para Android

O aplicativo Android fica em um projeto separado dentro de `android/` e reutiliza o downloader Python do repositório.

## Requisitos e instalação

- Android 10 (API 29) ou superior, em aparelho ARM64 (`arm64-v8a`).
- [Baixe o APK mais recente](https://github.com/gklein7/SnapGrab/releases/latest/download/SnapGrab-Android.apk) e abra-o no aparelho.
- Se solicitado, permita a instalação de aplicativos para o navegador ou gerenciador de arquivos que abriu o APK.

A distribuição é feita pelo APK assinado nas GitHub Releases, fora da Play Store. O app recebe links pelo menu Compartilhar ou por colagem, permite escolher vídeo/MP3 e qualidade, e salva o arquivo em `Downloads/SnapGrab`. A versão Android não inclui cookies de navegador, monitoramento contínuo da área de transferência, histórico nem nova tentativa.

## Build local

O workflow do GitHub Actions compila o APK de validação e o release. Para um build local em Linux ou WSL, são necessários JDK 17, Gradle 8.13, Android SDK Platform 35 e NDK 30.0.16248370. O script Bash baixa e verifica os fontes fixados de FFmpeg 8.1.3 e LAME 3.100, compila o binário ARM64 e o coloca no APK.

Na raiz do repositório:

```sh
android/scripts/build-ffmpeg.sh
gradle -p android :app:testDebugUnitTest :app:assembleDebug
```

O APK de debug fica em `android/app/build/outputs/apk/debug/app-debug.apk`. Os avisos de licenças também ficam embutidos em `android/app/src/main/assets/THIRD_PARTY_NOTICES.md`.

## Assinatura de release

O workflow assina versões de tags `v*` com um keystore persistente. Crie a chave uma única vez, guarde uma cópia de segurança segura e configure estes GitHub Actions Secrets no repositório:

- `ANDROID_KEYSTORE_BASE64`: keystore codificado em Base64.
- `ANDROID_KEY_ALIAS`: alias da chave.
- `ANDROID_KEYSTORE_PASSWORD`: senha do keystore.
- `ANDROID_KEY_PASSWORD`: senha da chave.

Exemplo para criar um keystore:

```sh
keytool -genkeypair -v -keystore snapgrab-release.jks -keyalg RSA -keysize 4096 -validity 10000 -alias snapgrab
base64 -w 0 snapgrab-release.jks
```

No PowerShell, gere o valor Base64 com:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("snapgrab-release.jks"))
```

Mantenha o mesmo keystore para todas as atualizações. Se ele for perdido, o APK publicado não poderá assinar uma atualização compatível para os usuários existentes. Nunca envie o keystore ao Git.
