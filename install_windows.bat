@echo off
echo 🚀 SL y TP Automatico para Bybit - Instalador Windows
echo =====================================================

echo.
echo 📋 Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python no encontrado. Por favor instala Python 3.8+ desde python.org
    pause
    exit /b 1
)

python --version
echo ✅ Python encontrado

echo.
echo 📦 Instalando dependencias...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ❌ Error instalando dependencias
    pause
    exit /b 1
)

echo.
echo ✅ Instalación completada exitosamente!
echo.
echo 🎯 Para ejecutar la aplicación:
echo    python pyside_trading_gui.py
echo    o
echo    python run.py
echo.
pause
