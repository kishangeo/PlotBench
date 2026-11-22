; PlotBench Windows installer (Inno Setup 6). Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
#define AppName "PlotBench"
#define AppVersion "1.32.1"

[Setup]
AppId={{6C1F7A52-3E7B-4F6E-9B0B-5D2A1C9E7B11}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Kishan Tiwari
AppContact=kishantiwari@iitkgp.ac.in
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=dist
OutputBaseFilename=PlotBench-{#AppVersion}-Setup
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64
ChangesAssociations=yes
UninstallDisplayIcon={app}\PlotBench.exe
SetupIconFile=plotbench\assets\icon.ico
WizardImageFile=plotbench\assets\wizard_large.bmp
WizardSmallImageFile=plotbench\assets\wizard_small.bmp

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
Name: "assoc"; Description: "Open .pbp project files with PlotBench"

[Files]
Source: "dist\PlotBench\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\PlotBench.exe"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\PlotBench.exe"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.pbp"; ValueType: string; ValueData: "PlotBench.Project"; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\PlotBench.Project\shell\open\command"; ValueType: string; ValueData: """{app}\PlotBench.exe"" ""%1"""; Flags: uninsdeletekey; Tasks: assoc

[Run]
Filename: "{app}\PlotBench.exe"; Description: "Launch PlotBench"; Flags: nowait postinstall skipifsilent
