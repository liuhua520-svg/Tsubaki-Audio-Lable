@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

set "MFA_ENV_DIR=C:\Users\Administrator\Downloads\files13\.mfa_env"
set "ENV_PY=C:\Users\Administrator\Downloads\files13\.mfa_env\python.exe"
set "PYTHONNOUSERSITE=1"

if not exist "%ENV_PY%" (
    echo Project env not found:
    echo %ENV_PY%
    pause
    exit /b 1
)

"%ENV_PY%" app.py
pause