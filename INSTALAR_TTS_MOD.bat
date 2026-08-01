@echo off
setlocal
cd /d "%~dp0"

:: Tenta usar o Python do venv primeiro
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe install_tts_mod_gui.py
    goto :FIM
)

:: Tenta usar o Python 3.12 instalado pelo instalar.bat
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" install_tts_mod_gui.py
    goto :FIM
)

:: Tenta o Python global
python install_tts_mod_gui.py

:FIM
if errorlevel 1 pause
