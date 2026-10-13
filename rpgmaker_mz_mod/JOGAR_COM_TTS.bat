@echo off
chcp 65001 >nul
title Iniciar Jogo RPG Maker com TTS Kokoro

echo ============================================================
echo   INICIANDO TTS BACKEND E JOGO (RPG MAKER MZ)
echo ============================================================
echo.

:: Iniciar o backend em uma nova janela
start "TTS Backend" cmd /c run_backend.bat

echo [*] Backend iniciado em nova janela.
echo [*] Aguardando servidor inicializar...
timeout /t 3 >nul

echo [*] Iniciando o jogo agora...
echo.

:: Localizar o executável do jogo (preferencialmente Game.exe)
set "GAME_EXE="
if exist "Game.exe" (
    set "GAME_EXE=Game.exe"
    goto :found_exe
)

for %%F in (*.exe) do (
    if /i not "%%F"=="python.exe" if /i not "%%F"=="pythonw.exe" if /i not "%%F"=="notification_helper.exe" (
        set "GAME_EXE=%%F"
        goto :found_exe
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
echo   Atalhos no Jogo:
echo     [V] Alternar Vozes TTS (Ligado/Desligado)
echo     [A] Alternar Avanco Automatico (Auto-Forward)
echo     [+] Aumentar Velocidade de Fala
echo     [-] Diminuir Velocidade de Fala
echo ============================================================
timeout /t 5
