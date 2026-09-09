# Instalador do AR Sandbox (Windows)

Esta pasta gera o **instalador único e 100% offline** do projeto:
`Output\AR-Sandbox-Setup-v6.0.exe` (~276 MB). O usuário final só precisa
de um Windows 10/11 64-bit — o instalador provê todo o resto.

## O que o instalador faz na máquina do usuário

1. Copia o projeto (código, mapa GeoTIFF de exemplo e documentação) para
   `C:\ARSandbox` (com permissão de escrita para usuários comuns, pois o
   app grava `calibration_data.json` e perfis na própria pasta);
2. Instala o **Python 3.12.10** (per-machine, silencioso) — se a máquina
   já tiver Python 3.12, reaproveita;
3. Cria o ambiente virtual `C:\ARSandbox\venv` e instala todas as
   dependências **offline**, a partir das wheels embutidas (numpy 1.26.4,
   opencv 4.11, rasterio, scipy, customtkinter, comtypes 1.3.1,
   pykinect2...);
4. Aplica automaticamente os **5 patches do pykinect2**
   (`patch_pykinect2.py` — cobre tanto a cópia do GitHub quanto a wheel
   do PyPI, que traz `sizeof(tagSTATSTG) == 72` fixo);
5. Instala o **Kinect for Windows Runtime v2.0** (silencioso; se já
   houver `Kinect20.dll` no sistema, pula). Sem Kinect físico o app cai
   automaticamente no modo simulação por mouse;
6. Roda um teste de fumaça dos imports e grava o log em
   `C:\ARSandbox\install.log`;
7. Cria os atalhos **AR Sandbox** e **AR Sandbox — Diagnóstico do
   Kinect** (Menu Iniciar e, opcionalmente, Área de Trabalho).

A desinstalação (Painel de Controle → AR Sandbox) remove `C:\ARSandbox`
por completo; o Python e o Kinect Runtime permanecem no sistema e podem
ser removidos separadamente.

## Como gerar o instalador (máquina de desenvolvimento)

Requisitos: Windows com internet, `py -3.11` (qualquer Python ≥3.9 com
pip serve — ajuste a chamada no script se necessário).

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
```

O script é idempotente e:

1. Baixa o instalador do Python 3.12.10 (python.org);
2. Baixa as wheels de todas as dependências do `requirements.txt`
   (alvo `cp312`/`win_amd64`, PyPI);
3. Baixa o Kinect Runtime v2.0 (download.microsoft.com, SHA1 conferido);
4. Gera o ícone `arsandbox.ico`;
5. Instala o Inno Setup 6 (per-user, silencioso), se ainda não houver;
6. Compila `ARSandbox.iss` → `Output\AR-Sandbox-Setup-v6.0.exe`.

## Arquivos

| Arquivo | Papel |
|---|---|
| `build_installer.ps1` | Gera o instalador (baixa payload + compila) |
| `ARSandbox.iss` | Script Inno Setup (empacotamento, atalhos, uninstall) |
| `bootstrap.ps1` | Roda no fim da instalação: Python → venv → wheels → patches → Kinect Runtime → teste |
| `patch_pykinect2.py` | Aplica os patches de compatibilidade do pykinect2 (idempotente) |
| `launchers/*.cmd` | Lançadores dos atalhos (usam o Python do venv) |
| `payload/` | (gerado, fora do git) Python + wheels + Kinect Runtime |
| `Output/` | (gerado, fora do git) instalador final |

## Teste do instalador

Instalação silenciosa (mesmo fluxo do modo gráfico):

```powershell
Output\AR-Sandbox-Setup-v6.0.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS=desktopicon
```

Depois confira `C:\ARSandbox\install.log` e rode o atalho "AR Sandbox".
Para validar o ambiente instalado por completo:

```powershell
C:\ARSandbox\venv\Scripts\python.exe -m pytest C:\ARSandbox\test_motor_caixao.py
```
