; Saberr — Inno Setup installer.
;
; Consumes a build output directory that contains:
;   <BuildPath>\main.dist\   (the Nuitka standalone dist — installed as  <app>\app\)
;   <BuildPath>\mariadb\     (the pruned MariaDB tree   — installed as  <app>\mariadb\)
;
; run: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" ./scripts/build/saberr_setup.iss
; run: ISCC.exe scripts\build\saberr_setup.iss
; override source dir: ISCC.exe /DBuildPath="C:\path\to\build" ...
; override dist folder name: ISCC.exe /DDistDirName="main.dist" ...
;
; The app version is the semver string from the bundled .app-version (may carry a -prerelease
; suffix). It drives the "Add/Remove Programs" entry, the setup filename, and the semver-aware
; downgrade guard in [Code]. The exe's numeric file-version (major.minor.patch.0) is not used here.

; ---- identity (NEVER change AppId across releases — it's the upgrade identity) ----
#define MyAppName    "Saberr"
#define MyAppPublisher "Saberr"
; AppId as Inno wants it in [Setup] (leading brace doubled so the value is a literal {GUID}):
#define MyAppId      "{{E9B4F2A7-3C61-4D8E-9F5A-2B7C1D6E8A04}"
; Same GUID in registry form (single braces) for reading the uninstall key in [Code]:
#define MyAppIdReg   "{E9B4F2A7-3C61-4D8E-9F5A-2B7C1D6E8A04}"

; ---- paths (all overridable via ISCC /D...) ----
#define RepoRoot     SourcePath + "\..\.."
#ifndef BuildPath
  #define BuildPath  RepoRoot + "\build"
#endif
#ifndef DistDirName
  #define DistDirName "main.dist"
#endif
#ifndef AppPort
  #define AppPort    "8125"
#endif
#ifndef Arch
  #define Arch       "x64"
#endif

#define SaberrExeSrc BuildPath + "\" + DistDirName + "\Saberr.exe"
#if !FileExists(SaberrExeSrc)
  #error Build output not found. Expected <BuildPath>\<DistDirName>\Saberr.exe — run the Nuitka build first, or pass /DBuildPath=...
#endif
; The installer's version is the true semver string the build wrote to .app-version (may carry a
; -prerelease suffix). Overridable via /DMyAppFullVersion=...; otherwise read from the bundled
; .app-version, whose first line must be 'app-ver=...'.
#ifndef MyAppFullVersion
  #define AppVerFH FileOpen(BuildPath + "\" + DistDirName + "\.app-version")
  #define AppVerLine Trim(FileRead(AppVerFH))
  #expr FileClose(AppVerFH)
  #if Pos("app-ver=", AppVerLine) != 1
    #error First line of .app-version must be 'app-ver=...'
  #endif
  #define MyAppFullVersion Trim(Copy(AppVerLine, 9, Len(AppVerLine)))
#endif

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppFullVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\app\Saberr.exe
UninstallDisplayName={#MyAppName}
OutputDir={#BuildPath}
OutputBaseFilename=Saberr-Setup-{#MyAppFullVersion}-{#Arch}
LicenseFile={#RepoRoot}\LICENSE
SetupIconFile={#RepoRoot}\assets\logo.ico
WizardStyle=modern dynamic
WizardSmallImageFile={#RepoRoot}\assets\logo.png
WizardImageFile={#RepoRoot}\assets\v-banner.png
WizardSmallImageFileDynamicDark={#RepoRoot}\assets\logo.png
WizardImageFileDynamicDark={#RepoRoot}\assets\v-banner.png
WizardImageStretch=yes
DisableWelcomePage=no
Compression=lzma2/max
SolidCompression=yes
; Program Files needs elevation; keep it admin so {autopf} = 64-bit Program Files.
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Windows 10 1903+ floor (matches the Python 3.13 / MariaDB baseline).
MinVersion=10.0.18362

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; Wipe the old program files before laying down the new bundle so orphaned files can't linger.
; NOTE: the data tree (%ProgramData%\Saberr) is intentionally never listed here.
[InstallDelete]
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\mariadb"

[Files]
Source: "{#BuildPath}\{#DistDirName}\*"; DestDir: "{app}\app"; \
    Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#BuildPath}\mariadb\*"; DestDir: "{app}\mariadb"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start-Menu shortcut + all-users Startup entry (both launch the tray).
; {commonstartup}, not {userstartup}: under an elevated install {userstartup} can point at the admin's
; profile, whereas a Startup-folder item launches at each login in that user's own unelevated context.
Name: "{group}\{#MyAppName}"; Filename: "{app}\app\Saberr.exe"; Parameters: "--tray"; WorkingDir: "{app}\app"
Name: "{commonstartup}\{#MyAppName}"; Filename: "{app}\app\Saberr.exe"; Parameters: "--tray"; WorkingDir: "{app}\app"

[Run]
; Firewall: drop any stale rule, then add an inbound allow for the backend port (LAN access is intended).
Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall delete rule name=""Saberr"""; \
    Flags: runhidden; StatusMsg: "Updating firewall rule..."
Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall add rule name=""Saberr"" dir=in action=allow protocol=TCP localport={#AppPort}"; \
    Flags: runhidden; StatusMsg: "Adding firewall rule..."
; Launch as the ORIGINAL (unelevated) user — never as admin, or the first-run data tree would be
; admin-owned and the app would lose the user's mapped-drive/SMB access.
Filename: "{app}\app\Saberr.exe"; Parameters: "--tray"; \
    Flags: postinstall nowait runasoriginaluser skipifsilent; \
    Description: "Start {#MyAppName} now"

[UninstallRun]
Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall delete rule name=""Saberr"""; \
    Flags: runhidden; RunOnceId: "DelSaberrFwRule"

[Code]
const
  SYNCHRONIZE = $00100000;
  SABERR_MUTEX = 'Global\SaberrTray';

var
  PrevVersion: String;   { installed version ('' if fresh install), set in InitializeSetup }

function OpenMutexW(dwDesiredAccess: LongWord; bInheritHandle: Boolean; lpName: String): THandle;
  external 'OpenMutexW@kernel32.dll stdcall';
function CloseHandle(hObject: THandle): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';

{ True while the tray (and therefore its child processes) is still running. }
function SaberrRunning(): Boolean;
var
  h: THandle;
begin
  h := OpenMutexW(SYNCHRONIZE, False, SABERR_MUTEX);
  Result := (h <> 0);
  if Result then
    CloseHandle(h);
end;

{ Signal a graceful shutdown (Saberr.exe --quit sets the tray's shutdown event), then wait for the
  tray to fully stop — up to ~30s. Never hard-kills (mariadbd datadir corruption). }
procedure StopSaberr(exePath: String);
var
  rc, i: Integer;
begin
  if not FileExists(exePath) then
    exit;
  if not SaberrRunning() then
    exit;
  Exec(exePath, '--quit', '', SW_HIDE, ewNoWait, rc);
  for i := 1 to 60 do
  begin
    if not SaberrRunning() then
      exit;
    Sleep(500);
  end;
end;

{ ---- SemVer parsing & comparison (major.minor.patch[-tag[.num]], +build metadata ignored) ---- }
type
  TSemVer = record
    Major, Minor, Patch, PreNum: Integer;
    PreTag: String;   { '' = final release, which outranks any prerelease of the same core }
  end;

{ Pop the substring up to the next `sep` (or the whole string if none), advancing `s` past it. }
function PopToken(var s: String; sep: String): String;
var p: Integer;
begin
  p := Pos(sep, s);
  if p = 0 then
  begin
    Result := s;
    s := '';
  end
  else
  begin
    Result := Copy(s, 1, p - 1);
    s := Copy(s, p + 1, Length(s));
  end;
end;

function ParseSemVer(s: String): TSemVer;
var core, pre: String;
begin
  Result.Major := 0; Result.Minor := 0; Result.Patch := 0;
  Result.PreNum := 0; Result.PreTag := '';
  s := Trim(s);
  s := PopToken(s, '+');        { drop build metadata }
  core := PopToken(s, '-');     { core = everything before the first '-' }
  pre := s;                     { pre = remainder (tag[.num]) or '' }
  Result.Major := StrToIntDef(PopToken(core, '.'), 0);
  Result.Minor := StrToIntDef(PopToken(core, '.'), 0);
  Result.Patch := StrToIntDef(PopToken(core, '.'), 0);   { missing patch -> 0 }
  if pre <> '' then
  begin
    Result.PreTag := PopToken(pre, '.');
    Result.PreNum := StrToIntDef(PopToken(pre, '.'), 0);
  end;
end;

{ SemVer precedence. Returns <0 if a<b, 0 if equal, >0 if a>b. }
function CompareSemVer(a, b: TSemVer): Integer;
begin
  Result := a.Major - b.Major;  if Result <> 0 then exit;
  Result := a.Minor - b.Minor;  if Result <> 0 then exit;
  Result := a.Patch - b.Patch;  if Result <> 0 then exit;
  if (a.PreTag = '') and (b.PreTag = '') then begin Result := 0;  exit; end;
  if a.PreTag = '' then begin Result := 1;  exit; end;   { release > prerelease }
  if b.PreTag = '' then begin Result := -1; exit; end;
  Result := CompareText(a.PreTag, b.PreTag);  if Result <> 0 then exit;
  Result := a.PreNum - b.PreNum;
end;

{ Locate a prior install via the uninstall registry key Inno writes. }
function GetPrevAppPath(var path: String): Boolean;
begin
  Result := RegQueryStringValue(HKLM,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppIdReg}_is1',
    'Inno Setup: App Path', path);
end;

{ The full semver string of an existing install ('' if none / unreadable). Prefers the true string
  from the previous build's .app-version; falls back to its numeric exe version for very old installs. }
function GetInstalledVersionStr(): String;
var
  prevPath, t: String;
  lines: TArrayOfString;
  i: Integer;
  ms, ls: Cardinal;
begin
  Result := '';
  if not GetPrevAppPath(prevPath) then
    exit;
  if LoadStringsFromFile(prevPath + '\app\.app-version', lines) then
    for i := 0 to GetArrayLength(lines) - 1 do
    begin
      t := Trim(lines[i]);
      if Copy(t, 1, 8) = 'app-ver=' then
      begin
        Result := Trim(Copy(t, 9, Length(t)));
        Break;
      end;
    end;
  if (Result = '') and GetVersionNumbers(prevPath + '\app\Saberr.exe', ms, ls) then
    Result := Format('%d.%d.%d', [ms shr 16, ms and $FFFF, ls shr 16]);
end;

{ Records the prior version and enforces the semver downgrade guard (migrations don't reverse). Runs before UI. }
function InitializeSetup(): Boolean;
begin
  Result := True;
  PrevVersion := GetInstalledVersionStr();
  if PrevVersion = '' then
    exit;
  if CompareSemVer(ParseSemVer('{#MyAppFullVersion}'), ParseSemVer(PrevVersion)) < 0 then
  begin
    MsgBox('A newer version of Saberr (' + PrevVersion + ') is already installed. Downgrade is not supported —'
           + #13#10 + 'please uninstall the current version first if you really want to go back.',
           mbError, MB_OK);
    Result := False;
  end;
end;

{ Reword the wizard so an existing install clearly reads as an upgrade/reinstall, not a fresh install. }
procedure InitializeWizard();
begin
  if PrevVersion = '' then
    exit;
  if PrevVersion = '{#MyAppFullVersion}' then
  begin
    WizardForm.WelcomeLabel1.Caption := 'Reinstall Saberr';
    WizardForm.WelcomeLabel2.Caption :=
      'Setup will reinstall Saberr version {#MyAppFullVersion} on your computer.'
      + #13#10#13#10 + 'Your existing database and settings will be kept.';
  end
  else
  begin
    WizardForm.WelcomeLabel1.Caption := 'Upgrade Saberr';
    WizardForm.WelcomeLabel2.Caption :=
      'Setup will upgrade Saberr from version ' + PrevVersion + ' to version {#MyAppFullVersion}.'
      + #13#10#13#10 + 'Your existing database and settings will be kept.';
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (CurPageID <> wpReady) or (PrevVersion = '') then
    exit;
  if PrevVersion = '{#MyAppFullVersion}' then
  begin
    WizardForm.PageNameLabel.Caption := 'Ready to Reinstall';
    WizardForm.PageDescriptionLabel.Caption := 'Setup is now ready to reinstall Saberr on your computer.';
    WizardForm.ReadyLabel.Caption :=
      'Saberr version {#MyAppFullVersion} will be reinstalled. Your database and settings will be kept.'
      + #13#10#13#10 + 'Click Install to continue.';
  end
  else
  begin
    WizardForm.PageNameLabel.Caption := 'Ready to Upgrade';
    WizardForm.PageDescriptionLabel.Caption := 'Setup is now ready to upgrade Saberr on your computer.';
    WizardForm.ReadyLabel.Caption :=
      'Saberr will be upgraded from version ' + PrevVersion + ' to version {#MyAppFullVersion}.'
      + #13#10 + 'Your database and settings will be kept.'
      + #13#10#13#10 + 'Click Install to continue.';
  end;
end;

{ Stop a running instance before overwriting its (locked) files on upgrade. }
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  NeedsRestart := False;
  StopSaberr(ExpandConstant('{app}\app\Saberr.exe'));
  if SaberrRunning() then
    Result := 'Saberr is still running and could not be stopped automatically.'
              + #13#10 + 'Please quit it from the tray icon, then run Setup again.'
  else
    Result := '';
end;

procedure CurUninstallStepChanged(CurStep: TUninstallStep);
var
  dataDir: String;
begin
  if CurStep = usUninstall then
    StopSaberr(ExpandConstant('{app}\app\Saberr.exe'))
  else if CurStep = usPostUninstall then
  begin
    dataDir := ExpandConstant('{commonappdata}\Saberr');
    if DirExists(dataDir) then
      if MsgBox('Also remove Saberr''s data (database, config, logs) at'
                + #13#10 + dataDir + '?'
                + #13#10 + 'This permanently deletes your library database and settings.',
                mbConfirmation, MB_YESNO) = IDYES then
        DelTree(dataDir, True, True, True);
  end;
end;