; Inno Setup Script for Transcription Studio
; ============================================
; Tailored for the PyInstaller build at dist\TranscriptionStudio\

#define MyAppName "Transcription Studio"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Juraj Mavračić"
#define MyAppURL "https://github.com/JurajMa/transcription"
#define MyAppExeName "TranscriptionStudio.exe"

[Setup]
; Unique App ID — generated once, keeps upgrades working
; DO NOT change this between versions
AppId={{B7E3F1A2-8D4C-4F5B-9A6E-1C2D3E4F5A6B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
; Install location
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; ====================================================
; DISCLAIMER — user MUST accept to continue installing
; ====================================================
LicenseFile=DISCLAIMER.txt
; Output settings
OutputDir=installer_output
OutputBaseFilename=TranscriptionStudio_Setup_{#MyAppVersion}
; Icon
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; Compression — lzma2/ultra gives the smallest installer
Compression=lzma2/ultra
SolidCompression=yes
; Require admin for Program Files
PrivilegesRequired=admin
; Windows 10+
MinVersion=10.0
; Modern wizard look
WizardStyle=modern
WizardSizePercent=120
; Misc
AllowNoIcons=yes
; Uninstall
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
; Customise the license page text so it says "Disclaimer" not "License Agreement"
WelcomeLabel2=This will install [name] on your computer.%n%nThe app requires your own OpenAI API key to function. You will be charged by OpenAI for API usage.%n%nClick Next to continue.
WizardLicense=Disclaimer && Terms of Use
LicenseLabel=Please read the following disclaimer and terms of use carefully.
LicenseLabel3=You must accept the following disclaimer and terms of use before installing [name]. Click "I accept" to continue.
LicenseAccepted=I &accept the disclaimer and terms of use
LicenseNotAccepted=I &do not accept

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Install everything from the PyInstaller dist folder recursively
Source: "dist\TranscriptionStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Also include the disclaimer in the install dir for reference
Source: "DISCLAIMER.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
; Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
; Start Menu → Uninstall
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; Launch after install checkbox
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent