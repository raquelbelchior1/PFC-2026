# build_installer.ps1 — Gera o instalador offline do AR Sandbox
# ==============================================================
# Rode este script UMA vez, na maquina de desenvolvimento (com internet):
#
#     powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
#
# Ele e idempotente (downloads ja feitos sao reaproveitados) e produz:
#
#     installer\Output\AR-Sandbox-Setup-v6.0.exe
#
# Esse .exe e o instalador final, 100% offline, para distribuir aos
# usuarios (pendrive, etc.). Etapas:
#   1. Baixa o instalador do Python 3.12 (python.org)
#   2. Baixa as wheels de todas as dependencias (PyPI, alvo cp312/win64)
#   3. Baixa o Kinect for Windows Runtime v2.0 (Microsoft)
#   4. Gera o icone arsandbox.ico
#   5. Instala o Inno Setup 6 (per-user, silencioso), se necessario
#   6. Compila ARSandbox.iss -> Setup final

$ErrorActionPreference = 'Stop'
$Installer = $PSScriptRoot
$Payload = Join-Path $Installer 'payload'
$Wheels  = Join-Path $Payload 'wheels'
New-Item -ItemType Directory -Force $Wheels | Out-Null

$PythonVer = '3.12.10'
$PythonExeName = "python-$PythonVer-amd64.exe"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVer/$PythonExeName"
# SHA1 esperado: 0f836c63e8c600b3989345ef637c8565b6f2d15c
$KinectUrl = 'https://download.microsoft.com/download/A/7/4/A74239EB-22C2-45A1-996C-2F8E564B28ED/KinectRuntime-v2.0_1409-Setup.exe'

function Baixar([string]$Url, [string]$Destino, [int64]$TamanhoMinimo) {
    if ((Test-Path $Destino) -and ((Get-Item $Destino).Length -ge $TamanhoMinimo)) {
        Write-Host "[ok] ja baixado: $(Split-Path $Destino -Leaf)"
        return
    }
    Write-Host "Baixando $Url ..."
    & curl.exe -L --fail --retry 3 -o $Destino $Url
    if ($LASTEXITCODE -ne 0) { throw "Download falhou: $Url" }
    if ((Get-Item $Destino).Length -lt $TamanhoMinimo) {
        throw "Download suspeito (arquivo pequeno demais): $Destino"
    }
}

# --------------------------------------------------------------------
Write-Host "`n=== 1/6 Instalador do Python $PythonVer ===" -ForegroundColor Cyan
Baixar $PythonUrl (Join-Path $Payload $PythonExeName) 20MB

# --------------------------------------------------------------------
Write-Host "`n=== 2/6 Wheels das dependencias (alvo: CPython 3.12 win_amd64) ===" -ForegroundColor Cyan
$req = Join-Path (Split-Path $Installer -Parent) 'requirements.txt'
& py -3.11 -m pip download -r $req -d $Wheels `
    --only-binary=:all: --python-version 312 --implementation cp --platform win_amd64 --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Download com --only-binary falhou; tentando construir wheels locais para pacotes sem wheel publicada...'
    # pykinect2 0.1.0 pode nao ter wheel: constroi localmente (pacote puro-Python)
    & py -3.11 -m pip wheel pykinect2==0.1.0 --no-deps -w $Wheels
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel obter a wheel do pykinect2.' }
    # Baixa o restante ignorando o pykinect2
    $reqSem = Join-Path $env:TEMP 'req_sem_pykinect2.txt'
    Get-Content $req | Where-Object { $_ -notmatch '^\s*pykinect2' } | Set-Content -Encoding utf8 $reqSem
    & py -3.11 -m pip download -r $reqSem -d $Wheels `
        --only-binary=:all: --python-version 312 --implementation cp --platform win_amd64 --quiet
    if ($LASTEXITCODE -ne 0) { throw 'pip download das dependencias falhou.' }
}
Write-Host "[ok] wheels em $Wheels"

# --------------------------------------------------------------------
Write-Host "`n=== 3/6 Kinect for Windows Runtime v2.0 ===" -ForegroundColor Cyan
Baixar $KinectUrl (Join-Path $Payload 'KinectRuntime-v2.0_1409-Setup.exe') 50MB

# --------------------------------------------------------------------
Write-Host "`n=== 4/6 Icone ===" -ForegroundColor Cyan
$IcoPath = Join-Path $Installer 'arsandbox.ico'
if (Test-Path $IcoPath) {
    Write-Host '[ok] arsandbox.ico ja existe'
} else {
    Add-Type -AssemblyName System.Drawing
    $bmp = New-Object System.Drawing.Bitmap 256, 256
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = 'AntiAlias'
    # Fundo: caixa de areia (marrom) com areia (bege) e "relevo" AR (verde/vermelho/azul)
    $g.Clear([System.Drawing.Color]::FromArgb(255, 94, 62, 36))
    $areia = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 224, 193, 138))
    $g.FillRectangle($areia, 24, 24, 208, 208)
    $verde = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 46, 160, 67))
    $verm  = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 205, 60, 50))
    $azul  = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 47, 111, 191))
    $g.FillRectangle($verm, 48, 48, 76, 76)
    $g.FillRectangle($azul, 132, 48, 76, 76)
    $g.FillRectangle($verde, 48, 132, 160, 76)
    $fonte = New-Object System.Drawing.Font 'Segoe UI', 44, ([System.Drawing.FontStyle]::Bold)
    $branco = [System.Drawing.Brushes]::White
    $fmt = New-Object System.Drawing.StringFormat
    $fmt.Alignment = 'Center'; $fmt.LineAlignment = 'Center'
    $g.DrawString('AR', $fonte, $branco, (New-Object System.Drawing.RectangleF 48, 132, 160, 76), $fmt)
    $g.Dispose()
    $ms = New-Object System.IO.MemoryStream
    $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
    $png = $ms.ToArray(); $ms.Dispose(); $bmp.Dispose()
    # Empacota o PNG num container .ico (formato PNG-in-ICO, Vista+)
    $fs = [System.IO.File]::Create($IcoPath)
    $bw = New-Object System.IO.BinaryWriter $fs
    $bw.Write([uint16]0); $bw.Write([uint16]1); $bw.Write([uint16]1)   # header: tipo icone, 1 imagem
    $bw.Write([byte]0); $bw.Write([byte]0)                             # 0 = 256px
    $bw.Write([byte]0); $bw.Write([byte]0)                             # paleta, reservado
    $bw.Write([uint16]1); $bw.Write([uint16]32)                        # planos, bpp
    $bw.Write([uint32]$png.Length); $bw.Write([uint32]22)              # tamanho, offset
    $bw.Write($png)
    $bw.Close(); $fs.Close()
    Write-Host "[ok] icone gerado: $IcoPath"
}

# --------------------------------------------------------------------
Write-Host "`n=== 5/6 Inno Setup 6 ===" -ForegroundColor Cyan
$iscc = $null
foreach ($c in @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
                 "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
                 "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")) {
    if (Test-Path $c) { $iscc = $c; break }
}
if (-not $iscc) {
    $isSetup = Join-Path $env:TEMP 'innosetup-installer.exe'
    Baixar 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe' $isSetup 3MB
    Write-Host 'Instalando Inno Setup 6 (per-user, silencioso)...'
    $p = Start-Process -FilePath $isSetup -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER' -Wait -PassThru
    if ($p.ExitCode -ne 0) { throw "Instalacao do Inno Setup falhou (codigo $($p.ExitCode))." }
    $iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    if (-not (Test-Path $iscc)) { throw 'ISCC.exe nao encontrado apos instalar o Inno Setup.' }
}
Write-Host "[ok] compilador: $iscc"

# --------------------------------------------------------------------
Write-Host "`n=== 6/6 Compilando o instalador ===" -ForegroundColor Cyan
& $iscc (Join-Path $Installer 'ARSandbox.iss')
if ($LASTEXITCODE -ne 0) { throw 'Compilacao do Inno Setup falhou.' }

$saida = Get-ChildItem (Join-Path $Installer 'Output') -Filter '*.exe' | Sort-Object LastWriteTime | Select-Object -Last 1
Write-Host "`n=== CONCLUIDO ===" -ForegroundColor Green
Write-Host "Instalador final: $($saida.FullName)  ($([math]::Round($saida.Length / 1MB)) MB)"
