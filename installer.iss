#define MyAppName "Ty-Videos-Studio"
#define MyAppVersion "1.1.1"
#define MyAppPublisher "Ty-Videos-Studio"
#define MyAppExeName "Ty-Videos-Studio.exe"

[Setup]
AppId={{9A6A7F3E-3F1B-4B55-9B6C-123456789ABC}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Ty-Videos-Studio
DefaultGroupName=Ty-Videos-Studio
OutputDir=installer_output
OutputBaseFilename=Ty-Videos-Studio-Setup
SetupIconFile=assets\app.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "dist\Ty-Videos-Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\app.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Ty-Videos-Studio"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"
Name: "{commondesktop}\Ty-Videos-Studio"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer Ty-Videos-Studio"; Flags: nowait postinstall skipifsilent
