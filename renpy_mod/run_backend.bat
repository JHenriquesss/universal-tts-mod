@echo off
chcp 65001 >nul
title Backend TTS Kokoro - Console de Monitoramento

echo ============================================================
echo   BACKEND TTS KOKORO - MONITORAMENTO LIVE
echo ============================================================
echo.
echo [*] Iniciando servidor TTS...
echo [*] Voce pode ver tudo o que acontece aqui.
echo [*] No jogo, aperte "v" para conectar a este console.
echo.

:: 1. Tentar usar o .venv local se existir
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)

:: 2. Tentar usar o .venv do projeto (3 niveis acima)
if exist "..\..\..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=..\..\..\.venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)

:: 3. Tentar o Python do PATH
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    goto :PYTHON_FOUND
)

:: 4. Tentar o Python 3.12 instalado pelo instalar.bat
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :PYTHON_FOUND
)

echo [ERRO] Python nao encontrado (.venv, PATH ou LOCALAPPDATA).
echo Execute o instalar.bat primeiro ou adicione python.exe ao PATH.
pause
exit /b 1

:PYTHON_FOUND

:: Executar o servidor. 
if exist "game\tts_server.py" (
    "%PYTHON_EXE%" "game\tts_server.py" %*
) else (
    "%PYTHON_EXE%" tts_server.py %*
)

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] O servidor TTS parou inesperadamente.
    pause
)
