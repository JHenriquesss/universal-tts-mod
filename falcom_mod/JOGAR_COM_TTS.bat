@echo off
setlocal
chcp 65001 >nul
title Trails in the Sky SC - Mod TTS & EXP Launcher
cd /d "%~dp0"

echo ============================================================
echo   TRAILS IN THE SKY SC - MOD TTS KOKORO ^& SPEEDHACK
echo ============================================================
echo   COMANDOS EM JOGO:
echo     [F1]        - Alternar Turbo 2x (Speedhack Falcom)
echo     [F2]        - Ligar / Desligar Vozes TTS (Mudo)
echo     [+] ou [-]  - Aumentar / Diminuir velocidade da fala
echo ============================================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "%~dp0falcom_launcher.py" %*
    goto :finished
)

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0falcom_launcher.py" %*
    goto :finished
)

set "PYTHON312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PYTHON312%" (
    "%PYTHON312%" "%~dp0falcom_launcher.py" %*
    goto :finished
)

where python >nul 2>&1
if not errorlevel 1 (
    python "%~dp0falcom_launcher.py" %*
    goto :finished
)

where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%~dp0falcom_launcher.py" %*
    goto :finished
)

where uv >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%P in ('uv python find 2^>nul') do set "PYTHON_EXE=%%P"
    if defined PYTHON_EXE (
        "%PYTHON_EXE%" "%~dp0falcom_launcher.py" %*
        goto :finished
    )
)

echo [ERRO] Python nao foi encontrado no PATH.
echo Instale Python 3 ou adicione python.exe ao PATH e tente novamente.
pause
exit /b 1

:finished
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%
