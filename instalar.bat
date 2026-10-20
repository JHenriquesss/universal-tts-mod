@echo off
chcp 65001 >nul
title Universal Kokoro TTS Mod - Instalador de Dependencias

echo ============================================================
echo   Universal Kokoro TTS Mod - Instalador de Dependencias
echo   Suporta: Ren'Py, Unity (BepInEx), Falcom ED6, RPG Maker MZ
echo ============================================================
echo.

:: 1. Verificar espeak-ng
espeak-ng --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] espeak-ng nao encontrado. Tentando instalar via winget...
    winget install --id eSpeak-NG.eSpeak-NG --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao instalar espeak-ng automaticamente.
        echo        Baixe e instale manualmente em: https://github.com/espeak-ng/espeak-ng/releases
        pause
        exit /b 1
    )
    echo [OK] espeak-ng instalado com sucesso.
) else (
    echo [OK] espeak-ng ja esta instalado.
)

:: 2. Localizar Python 3.12 com busca hierarquica
set "PYTHON_EXE="

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    goto :python_found
)

where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    goto :python_found
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :python_found
)

echo [!] Python 3.12 nao encontrado. Tentando instalar via winget...
winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar Python 3.12 via winget.
    echo        Instale o Python 3.12 manualmente em: https://www.python.org/downloads/
    pause
    exit /b 1
)
set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

:python_found
echo [OK] Python localizado: %PYTHON_EXE%

:: 3. Criar ambiente virtual se nao existir
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo [*] Criando ambiente virtual Python (.venv)...
    "%PYTHON_EXE%" -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao criar ambiente virtual .venv.
        pause
        exit /b 1
    )
    echo [OK] Ambiente virtual criado com sucesso.
) else (
    echo [OK] Ambiente virtual (.venv) ja existe.
)

:: 4. Instalar dependencias no ambiente virtual
echo.
echo [*] Atualizando pip e instalando dependencias (kokoro, sounddevice, soundfile, numpy)...
.venv\Scripts\pip.exe install --upgrade pip >nul 2>&1
.venv\Scripts\pip.exe install kokoro sounddevice soundfile numpy
if %errorlevel% neq 0 (
    echo [ERRO] Falha na instalacao das dependencias Python.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   [OK] Dependencias instaladas com sucesso!
echo ============================================================
echo.
echo   Proximo passo - Para instalar o mod em qualquer jogo:
echo     python install_tts_mod.py --game-folder "Caminho\Do\Jogo"
echo.
echo   Ou execute a interface grafica:
echo     python install_tts_mod_gui.py
echo.
pause
