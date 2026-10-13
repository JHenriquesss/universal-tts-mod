@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"
title Iniciar Jogo com TTS Kokoro

echo ============================================================
echo   INICIANDO TTS BACKEND E JOGO
echo ============================================================
echo.

set "READY_FILE=game\tts_ready.txt"
if not exist "game" if exist "tts_server.py" set "READY_FILE=tts_ready.txt"

if exist "%READY_FILE%" del "%READY_FILE%" >nul 2>&1

echo [*] Verificando conexao TTS na porta 5050...
netstat -ano | findstr ":5050 " | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo [*] Servidor TTS ja esta ativo na porta 5050.
    goto :find_game
)

echo [*] Iniciando o servidor TTS em nova janela...
start "TTS Backend" cmd /c run_backend.bat

echo [*] Aguardando inicializacao do modelo Kokoro TTS...
set /a ELAPSED=0
:wait_loop
if exist "%READY_FILE%" goto :ready
timeout /t 2 /nobreak >nul
set /a ELAPSED+=2
<nul set /p="."
if %ELAPSED% geq 60 (
    echo.
    echo [!] Tempo limite de espera atingido. Prosseguindo para abrir o jogo...
    goto :find_game
)
goto :wait_loop

:ready
echo.
echo [*] Servidor TTS pronto (!ELAPSED!s)!
echo.

:find_game
echo [*] Iniciando o jogo agora...
echo.

set "GAME_EXE="
for %%F in (*.exe) do (
    if /i not "%%F"=="python.exe" if /i not "%%F"=="pythonw.exe" (
        echo %%F | findstr /i /e /c:"-32.exe" >nul
        if errorlevel 1 (
            set "GAME_EXE=%%F"
            goto :found_exe
        )
    )
)

:found_exe
if defined GAME_EXE (
    start "" "%GAME_EXE%"
) else (
    echo [AVISO] Nenhum executavel do jogo encontrado no diretorio atual.
)

echo.
echo ============================================================
echo   Bom jogo!
echo ============================================================
timeout /t 5

