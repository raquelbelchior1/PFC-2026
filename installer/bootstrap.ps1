# bootstrap.ps1 — Etapa final do instalador do AR Sandbox
# ========================================================
# Executado pelo Setup (Inno Setup) com privilégios de administrador,
# após os arquivos do projeto e o payload serem copiados para $InstallDir.
#
# Etapas (todas offline — o payload traz tudo que é necessário):
#   1. Instala o Python 3.12 (per-machine), se ainda não existir
#   2. Cria o ambiente virtual em  $InstallDir\venv
#   3. Instala as dependências a partir das wheels do payload
#   4. Aplica os patches de compatibilidade do pykinect2
#   5. Instala o Kinect for Windows Runtime v2.0, se ainda não existir
#   6. Teste de fumaça dos imports principais
#
# Log completo em  $InstallDir\install.log
param(
    [Parameter(Mandatory = $true)][string]$InstallDir
)

$ErrorActionPreference = 'Stop'
$LogFile = Join-Path $InstallDir 'install.log'
Start-Transcript -Path $LogFile -Append | Out-Null

$Payload = Join-Path $InstallDir 'payload'
$Wheels  = Join-Path $Payload 'wheels'
$VenvDir = Join-Path $InstallDir 'venv'

function Write-Etapa([string]$msg) {
    Write-Host ''
    Write-Host "=== $msg ===" -ForegroundColor Cyan
}

function Falhar([string]$msg) {
    Write-Host ''
    Write-Host "ERRO: $msg" -ForegroundColor Red
    Write-Host "Log completo em: $LogFile"
    Stop-Transcript | Out-Null
    exit 1
}

# ---------------------------------------------------------------------------
# 1. Python 3.12
# ---------------------------------------------------------------------------
Write-Etapa 'Etapa 1/6 - Python 3.12'

function Get-Python312 {
    foreach ($hive in 'HKLM:', 'HKCU:') {
        foreach ($wow in 'SOFTWARE', 'SOFTWARE\WOW6432Node') {
            $key = "$hive\$wow\Python\PythonCore\3.12\InstallPath"
            if (Test-Path $key) {
                $dir = (Get-ItemProperty $key).'(default)'
                if ($dir) {
                    $exe = Join-Path $dir 'python.exe'
                    if (Test-Path $exe) { return $exe }
                }
            }
        }
    }
    return $null
}

$Python = Get-Python312
if ($Python) {
    Write-Host "Python 3.12 ja instalado: $Python"
} else {
    $pyInstaller = Get-ChildItem $Payload -Filter 'python-3.12*-amd64.exe' | Select-Object -First 1
    if (-not $pyInstaller) { Falhar 'Instalador do Python nao encontrado no payload.' }
    Write-Host "Instalando $($pyInstaller.Name) (modo silencioso, pode levar alguns minutos)..."
    $p = Start-Process -FilePath $pyInstaller.FullName -ArgumentList `
        '/quiet', 'InstallAllUsers=1', 'PrependPath=1', 'Include_launcher=1', 'Include_test=0', 'AssociateFiles=0' `
        -Wait -PassThru
    if ($p.ExitCode -ne 0 -and $p.ExitCode -ne 3010) {
        Falhar "Instalador do Python retornou codigo $($p.ExitCode)."
    }
    $Python = Get-Python312
    if (-not $Python) { Falhar 'Python 3.12 nao localizado apos a instalacao.' }
    Write-Host "Python 3.12 instalado: $Python"
}

# ---------------------------------------------------------------------------
# 2. Ambiente virtual
# ---------------------------------------------------------------------------
Write-Etapa 'Etapa 2/6 - Ambiente virtual (venv)'

$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
if (Test-Path $VenvPython) {
    Write-Host "Reaproveitando venv existente em $VenvDir"
} else {
    if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
    & $Python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
        Falhar 'Falha ao criar o ambiente virtual.'
    }
    Write-Host "venv criado em $VenvDir"
}

# ---------------------------------------------------------------------------
# 3. Dependências (offline, a partir das wheels do payload)
# ---------------------------------------------------------------------------
Write-Etapa 'Etapa 3/6 - Dependencias do projeto (offline)'

if (-not (Test-Path $Wheels)) { Falhar "Pasta de wheels nao encontrada: $Wheels" }
& $VenvPython -m pip install --no-index --find-links $Wheels -r (Join-Path $InstallDir 'requirements.txt')
if ($LASTEXITCODE -ne 0) { Falhar 'pip install das dependencias falhou (veja acima).' }

# ---------------------------------------------------------------------------
# 4. Patches do pykinect2
# ---------------------------------------------------------------------------
Write-Etapa 'Etapa 4/6 - Patches de compatibilidade do pykinect2'

& $VenvPython (Join-Path $InstallDir 'installer\patch_pykinect2.py')
if ($LASTEXITCODE -ne 0) { Falhar 'Aplicacao dos patches do pykinect2 falhou.' }

# ---------------------------------------------------------------------------
# 5. Kinect for Windows Runtime v2.0
# ---------------------------------------------------------------------------
Write-Etapa 'Etapa 5/6 - Kinect for Windows Runtime v2.0'

$kinectDll = Join-Path $env:windir 'System32\Kinect20.dll'
if (Test-Path $kinectDll) {
    Write-Host 'Kinect Runtime v2 ja instalado.'
} else {
    $kinectSetup = Get-ChildItem $Payload -Filter 'KinectRuntime*.exe' | Select-Object -First 1
    if (-not $kinectSetup) {
        Write-Host 'AVISO: instalador do Kinect Runtime nao encontrado no payload.' -ForegroundColor Yellow
        Write-Host 'O modo simulacao (mouse) funciona normalmente sem ele.'
    } else {
        Write-Host "Instalando $($kinectSetup.Name) (modo silencioso)..."
        $p = Start-Process -FilePath $kinectSetup.FullName -ArgumentList '/quiet', '/norestart' -Wait -PassThru
        if ($p.ExitCode -eq 0 -or $p.ExitCode -eq 3010) {
            Write-Host 'Kinect Runtime v2 instalado.'
            if ($p.ExitCode -eq 3010) {
                Write-Host 'AVISO: o Windows pede reinicializacao para concluir o driver do Kinect.' -ForegroundColor Yellow
            }
        } else {
            # Fallback: alguns ambientes rejeitam o modo silencioso —
            # abre o instalador com interface para o usuario concluir.
            Write-Host "Modo silencioso falhou (codigo $($p.ExitCode)); abrindo instalador com interface..." -ForegroundColor Yellow
            $p = Start-Process -FilePath $kinectSetup.FullName -Wait -PassThru
            if ($p.ExitCode -ne 0 -and $p.ExitCode -ne 3010) {
                Write-Host 'AVISO: Kinect Runtime nao foi instalado. O modo simulacao (mouse) continua funcional;' -ForegroundColor Yellow
                Write-Host "para usar o Kinect real, execute depois: $($kinectSetup.FullName)" -ForegroundColor Yellow
            }
        }
    }
}

# ---------------------------------------------------------------------------
# 6. Teste de fumaça
# ---------------------------------------------------------------------------
Write-Etapa 'Etapa 6/6 - Verificacao final'

# Passar codigo via "-c" a um exe nativo perde as aspas no PowerShell 5.1;
# escreve os testes em arquivos .py temporarios.
$smokeFile = Join-Path $env:TEMP 'arsandbox_smoke.py'
@'
import sys
print("Python:", sys.version)
import numpy;         print("numpy", numpy.__version__)
import cv2;           print("opencv", cv2.__version__)
import scipy;         print("scipy", scipy.__version__)
import rasterio;      print("rasterio", rasterio.__version__)
import customtkinter; print("customtkinter", customtkinter.__version__)
import comtypes;      print("comtypes", comtypes.__version__)
'@ | Set-Content -Encoding utf8 $smokeFile
& $VenvPython $smokeFile
if ($LASTEXITCODE -ne 0) { Falhar 'Teste de fumaca dos imports principais falhou.' }

# pykinect2 depende do Kinect Runtime — falha aqui nao e fatal
# (o app cai automaticamente no modo simulacao).
$smokeKinect = Join-Path $env:TEMP 'arsandbox_smoke_kinect.py'
@'
from pykinect2 import PyKinectV2
from pykinect2 import PyKinectRuntime
print("pykinect2 OK")
'@ | Set-Content -Encoding utf8 $smokeKinect
& $VenvPython $smokeKinect
if ($LASTEXITCODE -ne 0) {
    Write-Host 'AVISO: import do pykinect2 falhou - o modo Kinect real pode exigir reinicializacao do PC.' -ForegroundColor Yellow
}

Write-Host ''
Write-Host '=== Instalacao concluida com sucesso! ===' -ForegroundColor Green
Write-Host "Use o atalho 'AR Sandbox' da Area de Trabalho ou do Menu Iniciar."
Stop-Transcript | Out-Null
exit 0
