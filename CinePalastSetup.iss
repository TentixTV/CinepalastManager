; Inno Setup Script für CinePalast Manager
; Sie können dieses Skript in Inno Setup öffnen und kompilieren, um einen Windows-Installer (CinePalastSetup.exe) zu generieren.

[Setup]
; Eindeutige ID für die App
AppId={{5E583391-766F-48A0-A7EA-918991D4C63E}
AppName=CinePalast Manager
AppVersion=1.0
AppPublisher=Mannis Kinopalast
DefaultDirName={pf}\CinePalast Manager
DefaultGroupName=CinePalast Manager
OutputDir=.
OutputBaseFilename=CinePalastSetup
Compression=lzma
SolidCompression=yes
; Symbol-Datei für das Installationsprogramm (falls vorhanden, sonst Standard)
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\CinePalast.exe
WizardStyle=modern

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Hauptanwendung kopieren
Source: "dist\CinePalast.exe"; DestDir: "{app}"; Flags: ignoreversion
; Hinweis: Gecachte Ordner (assets/) und die Datenbank (cinepalast.db) werden 
; automatisch im selben Ordner erstellt, in dem die .exe gestartet wird.

[Icons]
; Verknüpfung im Startmenü erstellen
Name: "{group}\CinePalast Manager"; Filename: "{app}\CinePalast.exe"
; Verknüpfung auf dem Desktop erstellen
Name: "{commondesktop}\CinePalast Manager"; Filename: "{app}\CinePalast.exe"; Tasks: desktopicon

[Run]
; Option zum direkten Starten nach der Installation anbieten
Filename: "{app}\CinePalast.exe"; Description: "{cm:LaunchProgram,CinePalast Manager}"; Flags: nowait postinstall skipifsilent
