#!/usr/bin/env python3
"""
Script de ejecución para SL y TP Automático
Facilita el inicio de la aplicación con verificaciones previas
"""

import sys
import os
import subprocess
import importlib.util

def check_python_version():
    """Verificar versión de Python"""
    if sys.version_info < (3, 8):
        print("❌ Error: Se requiere Python 3.8 o superior")
        print(f"   Versión actual: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} - OK")
    return True

def check_dependencies():
    """Verificar dependencias requeridas"""
    required_packages = {
        'PySide6': 'PySide6',
        'pybit': 'pybit', 
        'requests': 'requests'
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        spec = importlib.util.find_spec(import_name)
        if spec is None:
            missing_packages.append(package_name)
            print(f"❌ {package_name} - No instalado")
        else:
            print(f"✅ {package_name} - OK")
    
    if missing_packages:
        print(f"\n⚠️  Faltan dependencias: {', '.join(missing_packages)}")
        print("💡 Para instalar, ejecuta:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Función principal"""
    print("🚀 SL y TP Automático para Bybit")
    print("=" * 40)
    
    # Verificar Python
    if not check_python_version():
        sys.exit(1)
    
    # Verificar dependencias
    print("\n📦 Verificando dependencias...")
    if not check_dependencies():
        sys.exit(1)
    
    # Verificar archivo principal
    main_file = "pyside_trading_gui.py"
    if not os.path.exists(main_file):
        print(f"❌ Error: No se encuentra {main_file}")
        sys.exit(1)
    
    print(f"\n✅ Todas las verificaciones pasaron")
    print("🎯 Iniciando aplicación...")
    print("-" * 40)
    
    # Ejecutar aplicación principal
    try:
        subprocess.run([sys.executable, main_file], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al ejecutar la aplicación: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Aplicación cerrada por el usuario")
        sys.exit(0)

if __name__ == "__main__":
    main()
