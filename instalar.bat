@echo off
chcp 65001 >nul
title Kokoro TTS - Instalação

echo ============================================================
echo   Kokoro TTS Mod para Ren'Py — Instalador
echo ============================================================
echo.

:: Verificar espeak-ng
espeak-ng --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] espeak-ng não encontrado. Instalando via winget...
    winget install --id eSpeak-NG.eSpeak-NG --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao instalar espeak-ng.
        echo        Baixe manualmente em: https://github.com/espeak-ng/espeak-ng/releases
        pause
        exit /b 1
    )
    echo [OK] espeak-ng instalado.
) else (
    echo [OK] espeak-ng já instalado.
)

:: Localizar Python 3.12
set PY312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PY312%" (
    echo [!] Python 3.12 não encontrado. Instalando via winget...
    winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao instalar Python 3.12.
        pause
        exit /b 1
    )
    echo [OK] Python 3.12 instalado.
) else (
    echo [OK] Python 3.12 encontrado.
)

:: Criar ambiente virtual se não existir
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo [*] Criando ambiente virtual Python 3.12...
    "%PY312%" -m venv .venv
    echo [OK] Ambiente virtual criado.
) else (
    echo [OK] Ambiente virtual já existe.
)

:: Instalar dependências
echo.
echo [*] Instalando dependências Python (pode demorar alguns minutos)...
.venv\Scripts\pip.exe install --upgrade pip >nul 2>&1
.venv\Scripts\pip.exe install kokoro sounddevice soundfile numpy
if %errorlevel% neq 0 (
    echo [ERRO] Falha na instalação das dependências.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   [OK] Instalação concluída com sucesso!
echo ============================================================
echo.
echo   Próximo passo:
echo   Copie  renpy_mod\tts_mod.rpy  para a pasta  game\  do jogo.
echo.
pause
