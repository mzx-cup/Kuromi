; Star-Learn (星识) Windows installer
; Run from project root:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\installer.iss
; Output: dist\Star-Learn-Setup-{AppVersion}.exe

#define MyAppName "Star-Learn (星识)"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Star-Learn"
#define MyAppURL "https://github.com/yourname/star-learn"
#define MyAppExeName "launcher.py"

[Setup]
AppId={{4F4B1F31-8E1C-4D9A-8D5A-1F2A3B4C5D6E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\Star-Learn
DefaultGroupName=Star-Learn (星识)
DisableProgramGroupPage=yes
LicenseFile=packaging\assets\LICENSE.txt
OutputDir=dist
OutputBaseFilename=Star-Learn-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\assets\icon.ico
SetupIconFile=packaging\assets\icon.ico
WizardImageFile=packaging\assets\installer-sidebar.bmp
WizardSmallImageFile=packaging\assets\installer-header.bmp
Uninstallable=yes
CloseApplicationsFilter=python.exe
CloseApplications=yes

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Files]
; Project source + assets (output of stage_payload.py)
Source: "packaging\app_payload\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Embedded CPython 3.11.x + site-packages (output of install_deps.py)
Source: "packaging\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs
; Branding assets (icon + wizard bmp + license)
Source: "packaging\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
; launcher.py at install root
Source: "packaging\launcher.py"; DestDir: "{app}"; Flags: ignoreversion
; starter .env template under <install>/packaging/templates
Source: "packaging\templates\starter.env"; DestDir: "{app}\packaging\templates"; Flags: ignoreversion

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式(&D)"; GroupDescription: "附加任务:"; Flags: unchecked

[Icons]
Name: "{group}\Star-Learn (星识)"; Filename: "{app}\python\python.exe"; Parameters: """{app}\launcher.py"""; IconFilename: "{app}\assets\icon.ico"
Name: "{autodesktop}\Star-Learn (星识)"; Filename: "{app}\python\python.exe"; Parameters: """{app}\launcher.py"""; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon
Name: "{group}\卸载 Star-Learn (星识)(&U)"; Filename: "{uninstallexe}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\打开数据目录(&O)"; Filename: "{userappdata}\StarLearn"

[UninstallDelete]
; Remove the install directory on uninstall, but KEEP %APPDATA%\StarLearn\
; (user data: .env, xingshi.db, logs, cache).  The user is prompted separately
; in the [Code] section to optionally wipe that folder.
Type: filesandordirs; Name: "{app}"

[Code]
// 卸载时询问用户是否删除 %APPDATA%\StarLearn\（默认保留）
function InitializeUninstall(): Boolean;
begin
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\StarLearn');
    if DirExists(DataDir) then
    begin
      if MsgBox(
        '是否同时删除您的星识 (Star-Learn) 用户数据？' + #13#10 +
        '位置: ' + DataDir + #13#10 + #13#10 +
        '包含: API 密钥 (.env)、学习数据 (xingshi.db)、日志、缓存。' + #13#10 + #13#10 +
        '选"否"将保留数据，便于以后重新安装后继续使用。',
        mbConfirmation, MB_YESNO) = IDYES
      then
      begin
        DelTree(DataDir, True, True, True);
      end;
    end;
  end;
end;
