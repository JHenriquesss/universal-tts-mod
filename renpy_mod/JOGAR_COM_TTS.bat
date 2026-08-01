@echo off
chcp 65001 >nul
title Iniciar Jogo com TTS Kokoro

echo ============================================================
echo   INICIANDO TTS BACKEND E JOGO
echo ============================================================
echo.

:: Iniciar o backend em uma nova janela
start "TTS Backend" cmd /c run_backend.bat

echo [*] Backend iniciado em nova janela.
echo [*] Iniciando o jogo agora...
echo.

:: Localizar o executável do jogo
set "GAME_EXE="
for %%F in (*.exe) do (
    :: Ignorar executáveis que não são o jogo
    if /i not "%%F"=="python.exe" if /i not "%%F"=="pythonw.exe" (
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
echo   Bom jogo!
echo ============================================================
timeout /t 5
