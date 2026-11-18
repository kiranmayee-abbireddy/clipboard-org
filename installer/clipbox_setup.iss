; Script generated for Inno Setup 6
; ClipBox - Aesthetic Clipboard Manager Installer

#define MyAppName "ClipBox"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "Kiranmayee Abbireddy"
#define MyAppURL "https://github.com/kiranmayee-abbireddy/clipboard-org"
#define MyAppExeName "ClipBox.exe"

[Setup]
; Basic Application Info
AppId={{9F5C4A3E-8B2D-4E1F-A6C7-3E9D1A2B5C8E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Destination Directories
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output Configuration
OutputDir=..\dist\installer
OutputBaseFilename=ClipBox-Setup-v1.2.0
SetupIconFile=..\clipbox.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression & Optimization
Compression=lzma2/ultra64
SolidCompression=yes

; Privileges & Compatibility
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Start ClipBox automatically on Windows login"; GroupDescription: "Windows Startup Options:"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\clipbox.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\clipbox.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\clipbox.ico"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
