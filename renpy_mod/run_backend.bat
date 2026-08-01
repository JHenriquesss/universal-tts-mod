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

:: Tentar localizar o Python 3.12 instalado pelo instalador.bat
set PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe

:: Tentar usar o .venv do projeto se estiver no caminho esperado (3 niveis acima)
if exist "..\..\..\.venv\Scripts\python.exe" (
    set PYTHON_EXE=..\..\..\.venv\Scripts\python.exe
)

if not exist "%PYTHON_EXE%" (
    :: Tentar o Python do PATH
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_EXE=python
    ) else (
        echo [ERRO] Python 3.12 nao encontrado.
        echo Execute o instalar.bat primeiro.
        pause
        exit /b 1
    )
)

:: Executar o servidor. 
if exist "game\tts_server.py" (
    "%PYTHON_EXE%" "game\tts_server.py"
) else (
    "%PYTHON_EXE%" tts_server.py
)

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] O servidor TTS parou inesperadamente.
    pause
)
