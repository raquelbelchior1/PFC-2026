@echo off
rem Diagnóstico do sensor Kinect v2 — verifica SDK, driver e captura.
chcp 65001 >nul
cd /d "%~dp0"
"venv\Scripts\python.exe" diagnostico_kinect.py
echo.
pause
