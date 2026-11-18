@echo off
setlocal
echo ==========================================
echo Rodando Suite Completa de Testes - TTS Mod
echo ==========================================
echo.

set PYTHONDONTWRITEBYTECODE=1
python -m unittest discover -s tests
set "TEST_STATUS=%errorlevel%"
if not "%TEST_STATUS%"=="0" (
    echo.
    echo [ERRO] A suite de testes falhou!
    exit /b %TEST_STATUS%
)

echo.
echo ==========================================
echo [SUCESSO] Todos os testes passaram!
echo ==========================================
pause
