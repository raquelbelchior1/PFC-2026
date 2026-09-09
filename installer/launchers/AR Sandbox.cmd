@echo off
rem Lançador do AR Sandbox — usa o Python do venv criado pelo instalador.
rem O cd garante que calibration_data.json e perfis sejam gravados na
rem pasta de instalação (gravável por usuários comuns).
chcp 65001 >nul
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo ERRO: ambiente Python nao encontrado. Reinstale o AR Sandbox.
    pause
    exit /b 1
)
"venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo O programa terminou com erro. Leia a mensagem acima.
    pause
)
