#!/bin/bash

echo "🏗️ SL y TP Automático - Constructor de Aplicación macOS"
echo "======================================================"

# Detectar Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PIP_CMD="pip"
else
    echo "❌ Python no encontrado. Por favor instala Python 3.8+"
    exit 1
fi

echo ""
echo "📋 Verificando Python y PyInstaller..."
$PYTHON_CMD --version

# Verificar PyInstaller
if ! $PYTHON_CMD -c "import PyInstaller" &> /dev/null; then
    echo "📦 PyInstaller no encontrado. Instalando..."
    $PIP_CMD install pyinstaller
    if [ $? -ne 0 ]; then
        echo "❌ Error instalando PyInstaller"
        exit 1
    fi
fi

echo "✅ Python y PyInstaller listos"

echo ""
echo "🧹 Limpiando builds anteriores..."
rm -rf dist build *.spec

echo ""
echo "🔨 Construyendo aplicación macOS..."
echo "   Esto puede tomar varios minutos..."

$PYTHON_CMD -m PyInstaller \
    --onefile \
    --windowed \
    --name "SL-TP-Automatico" \
    --icon="icon.icns" \
    --add-data "README.md:." \
    --hidden-import "PySide6.QtCore" \
    --hidden-import "PySide6.QtWidgets" \
    --hidden-import "PySide6.QtGui" \
    --hidden-import "pybit" \
    --hidden-import "requests" \
    --collect-all "PySide6" \
    --osx-bundle-identifier "com.codavidgarcia.sl-tp-automatico" \
    pyside_trading_gui.py

if [ $? -ne 0 ]; then
    echo "❌ Error durante la construcción"
    exit 1
fi

echo ""
echo "✅ ¡Aplicación creada exitosamente!"
echo ""
echo "📁 Ubicación: dist/SL-TP-Automatico"
echo "📏 Tamaño:"
ls -lh dist/SL-TP-Automatico | awk '{print "   " $5}'

echo ""
echo "🎯 Para distribuir:"
echo "   1. Copia el archivo dist/SL-TP-Automatico"
echo "   2. Los usuarios pueden ejecutarlo directamente"
echo "   3. No necesitan Python instalado"
echo ""

echo "🧪 ¿Deseas probar la aplicación ahora? [y/N]"
read -r test_app

if [[ $test_app =~ ^[Yy]$ ]]; then
    echo "🚀 Ejecutando..."
    open dist/SL-TP-Automatico
fi

echo ""
echo "✅ Proceso completado"

# Opcional: Crear DMG para distribución
echo ""
echo "📦 ¿Deseas crear un archivo DMG para distribución? [y/N]"
read -r create_dmg

if [[ $create_dmg =~ ^[Yy]$ ]]; then
    echo "📦 Creando DMG..."
    
    # Crear directorio temporal para DMG
    mkdir -p dmg_temp
    cp dist/SL-TP-Automatico dmg_temp/
    cp README.md dmg_temp/
    
    # Crear DMG
    hdiutil create -volname "SL-TP-Automatico" -srcfolder dmg_temp -ov -format UDZO dist/SL-TP-Automatico.dmg
    
    # Limpiar
    rm -rf dmg_temp
    
    if [ $? -eq 0 ]; then
        echo "✅ DMG creado: dist/SL-TP-Automatico.dmg"
    else
        echo "⚠️ Error creando DMG, pero la aplicación está lista"
    fi
fi
