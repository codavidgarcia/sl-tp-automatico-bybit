#!/bin/bash

echo "🚀 SL y TP Automático para Bybit - Instalador Unix/Linux/macOS"
echo "=============================================================="

# Verificar Python
echo ""
echo "📋 Verificando Python..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ Python no encontrado. Por favor instala Python 3.8+"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

$PYTHON_CMD --version
echo "✅ Python encontrado"

# Verificar pip
echo ""
echo "📦 Verificando pip..."
if ! command -v pip3 &> /dev/null; then
    if ! command -v pip &> /dev/null; then
        echo "❌ pip no encontrado. Por favor instala pip"
        exit 1
    else
        PIP_CMD="pip"
    fi
else
    PIP_CMD="pip3"
fi

echo "✅ pip encontrado"

# Crear entorno virtual (opcional pero recomendado)
echo ""
echo "🔧 ¿Deseas crear un entorno virtual? (recomendado) [y/N]"
read -r create_venv

if [[ $create_venv =~ ^[Yy]$ ]]; then
    echo "📁 Creando entorno virtual..."
    $PYTHON_CMD -m venv venv
    
    # Activar entorno virtual
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    
    echo "✅ Entorno virtual creado y activado"
    PIP_CMD="pip"  # Usar pip del entorno virtual
fi

# Instalar dependencias
echo ""
echo "📦 Instalando dependencias..."
$PIP_CMD install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Error instalando dependencias"
    exit 1
fi

echo ""
echo "✅ Instalación completada exitosamente!"
echo ""
echo "🎯 Para ejecutar la aplicación:"
if [[ $create_venv =~ ^[Yy]$ ]]; then
    echo "   1. Activa el entorno virtual:"
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        echo "      source venv/Scripts/activate"
    else
        echo "      source venv/bin/activate"
    fi
    echo "   2. Ejecuta la aplicación:"
fi
echo "      $PYTHON_CMD pyside_trading_gui.py"
echo "      o"
echo "      $PYTHON_CMD run.py"
echo ""
