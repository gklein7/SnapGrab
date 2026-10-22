#define MyAppName "SnapGrab"
#ifndef MyAppVersion
  #define MyAppVersion "1.1.0"
#endif
#define MyAppPublisher "SnapGrab Contributors"
#define MyAppExeName "SnapGrab.exe"
#define PyInstallerOutput "..\dist\SnapGrab"

[Setup]
AppId={{6F77292F-E4F8-47BC-9358-7C6D79D43A60}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
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

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked
Name: "startup"; Description: "Iniciar o SnapGrab com o Windows"; GroupDescription: "Opções:"

[Files]
Source: "{#PyInstallerOutput}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\SnapGrab"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\SnapGrab"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\SnapGrab"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar o SnapGrab"; Flags: postinstall nowait skipifsilent
