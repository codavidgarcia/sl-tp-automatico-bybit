@echo off
echo 🏗️ SL y TP Automatico - Constructor de Ejecutable Windows
echo ========================================================

echo.
echo 📋 Verificando Python y PyInstaller...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python no encontrado. Por favor instala Python 3.8+ desde python.org
    pause
    exit /b 1
)

python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📦 PyInstaller no encontrado. Instalando...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo ❌ Error instalando PyInstaller
        pause
        exit /b 1
    )
)

echo ✅ Python y PyInstaller listos

echo.
echo 🧹 Limpiando builds anteriores...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del "*.spec"

echo.
echo 🔨 Construyendo ejecutable...
echo    Esto puede tomar varios minutos...

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "SL-TP-Automatico" ^
    --icon=icon.ico ^
    --add-data "README.md;." ^
    --hidden-import "PySide6.QtCore" ^
    --hidden-import "PySide6.QtWidgets" ^
    --hidden-import "PySide6.QtGui" ^
    --hidden-import "pybit" ^
    --hidden-import "requests" ^
    --collect-all "PySide6" ^
    pyside_trading_gui.py

if %errorlevel% neq 0 (
    echo ❌ Error durante la construcción
    pause
    exit /b 1
)

echo.
echo ✅ ¡Ejecutable creado exitosamente!
echo.
echo 📁 Ubicación: dist\SL-TP-Automatico.exe
echo 📏 Tamaño: 
for %%A in ("dist\SL-TP-Automatico.exe") do echo    %%~zA bytes

echo.
echo 🎯 Para distribuir:
echo    1. Copia el archivo dist\SL-TP-Automatico.exe
echo    2. Los usuarios pueden ejecutarlo directamente
echo    3. No necesitan Python instalado
echo.

echo 🧪 ¿Deseas probar el ejecutable ahora? [y/N]
set /p test_exe=
if /i "%test_exe%"=="y" (
    echo 🚀 Ejecutando...
    start "" "dist\SL-TP-Automatico.exe"
)

echo.
echo ✅ Proceso completado
pause
