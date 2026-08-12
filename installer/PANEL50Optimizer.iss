#define MyAppName "PNL50 PC OPTIMIZER PRO"
#define MyAppVersion "1.0"
#define MyAppPublisher "PANEL 50"
#define MyAppExeName "PNL50 PC OPTIMIZER PRO.exe"

[Setup]
AppId={{D3C6C5BD-9C7B-4F6B-BF0A-50C1F5FEF00A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\PNL50 PC OPTIMIZER PRO
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=PNL50-PC-OPTIMIZER-PRO-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=..\assets\panel50.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\PNL50 PC OPTIMIZER PRO.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
