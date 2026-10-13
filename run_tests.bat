@echo off
setlocal
echo ==========================================
echo Rodando Suite Completa de Testes - TTS Mod
echo ==========================================
echo.

set PYTHONDONTWRITEBYTECODE=1
python -m unittest discover -s tests
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] A suite de testes falhou!
    exit /b %errorlevel%
)

echo.
echo ==========================================
echo [SUCESSO] Todos os 136+ testes passaram!
echo ==========================================
pause
