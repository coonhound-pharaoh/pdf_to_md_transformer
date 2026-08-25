; Inno Setup script for PDF to MD Transformer (Windows x64)
; Built in CI: ISCC packaging\windows\installer.iss

#define MyAppName "PDF to MD Transformer"
#define MyAppVersion "1.1.0"
#define MyAppExeName "PDF-to-MD-Transformer.exe"

[Setup]
AppId={{7E1F63C2-9A0B-4C5D-B1E4-52A9D3F0AC21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Michael Macauley (open source, MIT)
DefaultDirName={autopf}\PDF to MD Transformer
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
OutputDir=..\..\installer-output
OutputBaseFilename=PDF-to-MD-Transformer-Setup-win-x64
SetupIconFile=..\..\assets\icon.ico
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion
; Bundled Tesseract OCR engine (Apache-2.0), staged by CI into bundle\
Source: "..\..\bundle\Tesseract-OCR\*"; DestDir: "{app}\Tesseract-OCR"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
