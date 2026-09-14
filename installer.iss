#define MyAppName "VideoForge Studio"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "VideoForge Studio"
#define MyAppExeName "VideoForge-Studio.exe"

[Setup]
AppId={{9A6A7F3E-3F1B-4B55-9B6C-VIDEOFORGESTUDIO}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\VideoForge Studio
DefaultGroupName=VideoForge Studio
OutputDir=installer_output
OutputBaseFilename=VideoForge-Studio-Setup
SetupIconFile=assets\app.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "dist\VideoForge-Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\VideoForge Studio"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"
Name: "{commondesktop}\VideoForge Studio"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer VideoForge Studio"; Flags: nowait postinstall skipifsilent
