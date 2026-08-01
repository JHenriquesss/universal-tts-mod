@echo off
echo ==========================================
echo Rodando Suite de Testes - Ren'Py TTS Mod
echo ==========================================
echo.

echo [1/2] Rodando Testes Unitarios (TextCleaner)...
python tests/test_cleaner.py
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Testes unitarios falharam!
    exit /b %errorlevel%
)

echo.
echo [2/2] Rodando Testes de Integracao (Servidor)...
python tests/test_server.py
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Testes de integracao falharam!
    exit /b %errorlevel%
)

echo.
echo ==========================================
echo [SUCESSO] Todos os testes passaram!
echo ==========================================
pause
