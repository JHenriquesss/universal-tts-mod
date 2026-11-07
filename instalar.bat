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

:: Pacotes do backend: Kokoro no ONNX Runtime, sem PyTorch.
:: misaki vai sem o extra [en], que puxaria o torch por um plugin do spacy.
set "TTS_PACKAGES=onnxruntime kokoro-onnx misaki num2words spacy sounddevice soundfile numpy"

:: 4. Instalar dependencias no ambiente virtual
echo.
echo [*] Atualizando pip e instalando dependencias (%TTS_PACKAGES%)...
.venv\Scripts\pip.exe install --upgrade pip >nul 2>&1
.venv\Scripts\pip.exe install %TTS_PACKAGES%
if %errorlevel% neq 0 (
    echo [ERRO] Falha na instalacao das dependencias Python.
    pause
    exit /b 1
)

:: 5. Runtime leve do backend, compartilhado por todos os jogos.
set "TTS_RUNTIME=%LOCALAPPDATA%\UniversalKokoroTTS\runtime"
echo.
echo [*] Preparando runtime leve do backend em "%TTS_RUNTIME%"...
if not exist "%TTS_RUNTIME%\Scripts\python.exe" (
    "%PYTHON_EXE%" -m venv "%TTS_RUNTIME%"
)
"%TTS_RUNTIME%\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
"%TTS_RUNTIME%\Scripts\python.exe" -m pip install %TTS_PACKAGES%
"%TTS_RUNTIME%\Scripts\python.exe" -m spacy download en_core_web_sm
set "RUNTIME_STATUS=%errorlevel%"
:: Restos do antigo motor PyTorch (runtime criado por versoes anteriores).
"%TTS_RUNTIME%\Scripts\python.exe" -m pip uninstall -y kokoro torch transformers spacy-curated-transformers curated-transformers curated-tokenizers >nul 2>&1
if %RUNTIME_STATUS% neq 0 (
    echo [AVISO] Runtime leve incompleto. O backend usara o Python encontrado acima.
) else (
    echo [OK] Runtime leve pronto.
)

:: 6. Modelo Kokoro-82M (ONNX) e vozes, compartilhados por todos os jogos.
set "TTS_MODELS=%LOCALAPPDATA%\UniversalKokoroTTS\onnx"
set "TTS_MODEL_URL=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
echo.
echo [*] Verificando modelo Kokoro em "%TTS_MODELS%"...
if not exist "%TTS_MODELS%" mkdir "%TTS_MODELS%"
for %%F in (kokoro-v1.0.onnx voices-v1.0.bin) do (
    if not exist "%TTS_MODELS%\%%F" (
        echo [*] Baixando %%F...
        curl -L --fail -o "%TTS_MODELS%\%%F.part" "%TTS_MODEL_URL%/%%F" && move /y "%TTS_MODELS%\%%F.part" "%TTS_MODELS%\%%F" >nul
    )
)
if not exist "%TTS_MODELS%\kokoro-v1.0.onnx" goto :model_missing
if not exist "%TTS_MODELS%\voices-v1.0.bin" goto :model_missing
echo [OK] Modelo Kokoro pronto.
goto :model_done

:model_missing
echo [ERRO] Falha ao baixar o modelo Kokoro. Verifique a internet e rode o instalador de novo.
pause
exit /b 1

:model_done

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
