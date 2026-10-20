@echo off
setlocal
set SCRIPT_DIR=%~dp0
set VBS_TARGET=%SCRIPT_DIR%iniciar_silencioso.vbs
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_FOLDER%\MediaDownloader.lnk

echo Criando atalho na inicializacao do Windows...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%VBS_TARGET%\"'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo [SUCESSO] O programa agora iniciara automaticamente com o Windows em segundo plano!
    echo Local: %SHORTCUT_PATH%
) else (
    echo [ERRO] Nao foi possivel criar o atalho.
)
echo.
pause
