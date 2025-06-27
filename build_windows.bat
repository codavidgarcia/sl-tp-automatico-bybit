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
echo 📦 Comprimiendo para distribución...
cd dist
if exist "SL-TP-Automatico.exe" (
    powershell Compress-Archive -Path "SL-TP-Automatico.exe" -DestinationPath "SL-TP-Automatico-Windows-v1.1.0.zip" -Force
    echo ✅ Archivo comprimido: SL-TP-Automatico-Windows-v1.1.0.zip
    for %%A in ("SL-TP-Automatico-Windows-v1.1.0.zip") do echo    Tamaño comprimido: %%~zA bytes
) else (
    echo ❌ No se encontró el ejecutable para comprimir
)
cd ..

echo.
echo 🎯 Archivos listos para distribución:
echo    📁 dist\SL-TP-Automatico.exe (ejecutable)
echo    📦 dist\SL-TP-Automatico-Windows-v1.1.0.zip (para subir al repo)
echo.
echo 💡 Los usuarios pueden:
echo    1. Descargar y ejecutar directamente el .exe
echo    2. No necesitan Python instalado
echo    3. Funciona en Windows 10/11
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
