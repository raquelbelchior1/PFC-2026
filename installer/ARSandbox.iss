; ARSandbox.iss - Instalador do AR Sandbox (PFC-2026)
; =====================================================
; Compilar com Inno Setup 6:  ISCC.exe ARSandbox.iss
; (ou simplesmente rodar  build_installer.ps1 , que baixa o payload,
;  instala o Inno Setup se preciso e compila este script)
;
; O Setup gerado e 100% offline: embute o instalador do Python 3.12,
; todas as wheels das dependencias e o Kinect Runtime v2.0.

#define MyAppName "AR Sandbox - Caixao de Areia"
#define MyAppVersion "6.0"
#define MyAppPublisher "PFC-2026 (AMAN)"
#define ProjRoot ".."

[Setup]
AppId={{B7E2A9D4-4C1F-4E8A-9B3D-7A2F0C5E8D14}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={sd}\ARSandbox
DisableProgramGroupPage=yes
; Admin: necessario para instalar Python (per-machine) e Kinect Runtime
PrivilegesRequired=admin
OutputDir=Output
OutputBaseFilename=AR-Sandbox-Setup-v{#MyAppVersion}
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=arsandbox.ico
UninstallDisplayIcon={app}\arsandbox.ico

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; --- Codigo do projeto -------------------------------------------------
Source: "{#ProjRoot}\main.py";                 DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjRoot}\kinect_sensor.py";        DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjRoot}\motor_caixao_areia.py";   DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjRoot}\mde_cartografia.py";      DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjRoot}\diagnostico_kinect.py";   DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjRoot}\test_motor_caixao.py";    DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjRoot}\requirements.txt";        DestDir: "{app}"; Flags: ignoreversion
; --- Mapa GeoTIFF de exemplo ------------------------------------------
Source: "{#ProjRoot}\25S51_ZN.tif";            DestDir: "{app}"; Flags: ignoreversion
; --- Documentacao ------------------------------------------------------
Source: "{#ProjRoot}\README.md";                     DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjRoot}\DOCUMENTACAO_OFICIAL.md";       DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjRoot}\GUIA_CALIBRACAO_PROJETOR.md";   DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjRoot}\GUIA_INSTALACAO_INICIANTES.md"; DestDir: "{app}"; Flags: ignoreversion
; --- Instalador / bootstrap -------------------------------------------
Source: "bootstrap.ps1";        DestDir: "{app}\installer"; Flags: ignoreversion
Source: "patch_pykinect2.py";   DestDir: "{app}\installer"; Flags: ignoreversion
Source: "launchers\*.cmd";      DestDir: "{app}";           Flags: ignoreversion
Source: "arsandbox.ico";        DestDir: "{app}";           Flags: ignoreversion
; --- Payload offline (Python + wheels + Kinect Runtime) ---------------
Source: "payload\*"; DestDir: "{app}\payload"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; O app grava calibration_data.json / perfis na propria pasta -> usuarios
; comuns precisam de permissao de escrita mesmo com instalacao como admin.
Name: "{app}"; Permissions: users-modify

[Icons]
Name: "{autoprograms}\AR Sandbox";                    Filename: "{app}\AR Sandbox.cmd";             WorkingDir: "{app}"; IconFilename: "{app}\arsandbox.ico"
Name: "{autoprograms}\AR Sandbox - Diagnostico do Kinect"; Filename: "{app}\Diagnostico do Kinect.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\arsandbox.ico"
Name: "{autodesktop}\AR Sandbox";                     Filename: "{app}\AR Sandbox.cmd";             WorkingDir: "{app}"; IconFilename: "{app}\arsandbox.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\AR Sandbox.cmd"; Description: "Executar o AR Sandbox agora"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Remove tambem o que foi criado depois da instalacao (venv, logs,
; calibracao, __pycache__). O Python e o Kinect Runtime permanecem no
; sistema (podem ser desinstalados pelo Painel de Controle).
Type: filesandordirs; Name: "{app}"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Cmd: String;
begin
  if CurStep = ssPostInstall then
  begin
    WizardForm.StatusLabel.Caption :=
      'Instalando Python, dependencias e Kinect Runtime (pode levar varios minutos)...';
    Cmd := '-NoProfile -ExecutionPolicy Bypass -File "' +
           ExpandConstant('{app}\installer\bootstrap.ps1') +
           '" -InstallDir "' + ExpandConstant('{app}') + '"';
    if not Exec('powershell.exe', Cmd, '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
    begin
      MsgBox('Nao foi possivel executar o script de configuracao (bootstrap.ps1).' + #13#10 +
             'Execute manualmente como administrador: ' + #13#10 +
             ExpandConstant('{app}\installer\bootstrap.ps1'), mbError, MB_OK);
    end
    else if ResultCode <> 0 then
    begin
      MsgBox('A configuracao do ambiente terminou com erro (codigo ' + IntToStr(ResultCode) + ').' + #13#10 +
             'Consulte o log: ' + ExpandConstant('{app}\install.log') + #13#10#13#10 +
             'Para tentar de novo, execute como administrador:' + #13#10 +
             'powershell -ExecutionPolicy Bypass -File "' +
             ExpandConstant('{app}\installer\bootstrap.ps1') + '" -InstallDir "' +
             ExpandConstant('{app}') + '"', mbError, MB_OK);
    end;
  end;
end;
