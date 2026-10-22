#define MyAppName "SnapGrab"
#ifndef MyAppVersion
  #define MyAppVersion "1.1.1"
#endif
#define MyAppPublisher "gklein7"
#define MyAppExeName "SnapGrab.exe"
#define PyInstallerOutput "..\dist\SnapGrab"

[Setup]
AppId={{6F77292F-E4F8-47BC-9358-7C6D79D43A60}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/gklein7
AppSupportURL=https://github.com/gklein7/SnapGrab
AppUpdatesURL=https://github.com/gklein7/SnapGrab/releases/latest
DefaultDirName={localappdata}\Programs\SnapGrab
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=SnapGrab-Setup
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\SnapGrab.ico

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked
Name: "startup"; Description: "Iniciar o SnapGrab com o Windows"; GroupDescription: "Opções:"

[Files]
Source: "{#PyInstallerOutput}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\SnapGrab"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\SnapGrab"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\SnapGrab"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar o SnapGrab"; Flags: postinstall nowait skipifsilent
