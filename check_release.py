#!/usr/bin/env python3
"""
Script de verificación para preparación de release
Verifica que todos los archivos estén listos para publicación
"""

import os
import sys
import subprocess
from pathlib import Path

def check_file_exists(file_path, description):
    """Verificar que un archivo existe"""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} - NO ENCONTRADO")
        return False

def check_python_syntax(file_path):
    """Verificar sintaxis de Python"""
    try:
        result = subprocess.run([sys.executable, '-m', 'py_compile', file_path], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Sintaxis válida: {file_path}")
            return True
        else:
            print(f"❌ Error de sintaxis en {file_path}: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error verificando {file_path}: {e}")
        return False

def check_imports(file_path):
    """Verificar que los imports funcionen"""
    try:
        # Cambiar al directorio del archivo para imports relativos
        original_dir = os.getcwd()
        os.chdir(os.path.dirname(file_path))
        
        result = subprocess.run([sys.executable, '-c', f'import {os.path.basename(file_path)[:-3]}'], 
                              capture_output=True, text=True)
        
        os.chdir(original_dir)
        
        if result.returncode == 0:
            print(f"✅ Imports válidos: {file_path}")
            return True
        else:
            print(f"⚠️ Advertencia en imports de {file_path}: {result.stderr}")
            return True  # No es crítico para release
    except Exception as e:
        print(f"⚠️ Error verificando imports de {file_path}: {e}")
        return True  # No es crítico para release

def main():
    """Función principal de verificación"""
    print("🔍 Verificando preparación para release...")
    print("=" * 50)
    
    # Cambiar al directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    all_checks_passed = True
    
    # Verificar archivos principales
    print("\n📁 Verificando archivos principales:")
    main_files = [
        ("pyside_trading_gui.py", "Interfaz principal"),
        ("trading_engine.py", "Motor de trading"),
        ("config_manager.py", "Gestor de configuración"),
        ("run.py", "Script de ejecución"),
        ("requirements.txt", "Dependencias"),
        ("README.md", "Documentación principal"),
        ("LICENSE", "Licencia"),
        (".gitignore", "Configuración Git"),
        ("VERSION.md", "Información de versión")
    ]
    
    for file_path, description in main_files:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    # Verificar sintaxis de archivos Python
    print("\n🐍 Verificando sintaxis de Python:")
    python_files = [
        "pyside_trading_gui.py",
        "trading_engine.py", 
        "config_manager.py",
        "run.py"
    ]
    
    for file_path in python_files:
        if os.path.exists(file_path):
            if not check_python_syntax(file_path):
                all_checks_passed = False
    
    # Verificar imports (no crítico)
    print("\n📦 Verificando imports:")
    for file_path in python_files:
        if os.path.exists(file_path):
            check_imports(file_path)
    
    # Verificar archivos de construcción
    print("\n🏗️ Verificando archivos de construcción:")
    build_files = [
        ("build.py", "Constructor universal"),
        ("build_windows.bat", "Constructor Windows"),
        ("build_mac.sh", "Constructor macOS"),
        ("install_windows.bat", "Instalador Windows"),
        ("install_unix.sh", "Instalador Unix")
    ]
    
    for file_path, description in build_files:
        check_file_exists(file_path, description)
    
    # Verificar que no hay archivos sensibles
    print("\n🔒 Verificando archivos sensibles:")
    sensitive_files = [
        "config.json",
        "*.key",
        "api_credentials.json",
        "credentials.enc"
    ]
    
    for pattern in sensitive_files:
        if '*' in pattern:
            import glob
            files = glob.glob(pattern)
            if files:
                print(f"⚠️ Archivos sensibles encontrados: {files}")
                print("   Asegúrate de que estén en .gitignore")
        else:
            if os.path.exists(pattern):
                print(f"⚠️ Archivo sensible encontrado: {pattern}")
                print("   Asegúrate de que esté en .gitignore")
    
    # Verificar .gitignore
    print("\n🚫 Verificando .gitignore:")
    if os.path.exists('.gitignore'):
        with open('.gitignore', 'r') as f:
            gitignore_content = f.read()
            
        required_patterns = [
            '__pycache__/',
            '*.pyc',
            'config.json',
            '*.key',
            'build/',
            'dist/'
        ]
        
        for pattern in required_patterns:
            if pattern in gitignore_content:
                print(f"✅ .gitignore incluye: {pattern}")
            else:
                print(f"⚠️ .gitignore no incluye: {pattern}")
    
    # Resultado final
    print("\n" + "=" * 50)
    if all_checks_passed:
        print("🎉 ¡Todos los checks críticos pasaron!")
        print("✅ El proyecto está listo para release")
        print("\n📋 Próximos pasos:")
        print("   1. Ejecutar tests finales")
        print("   2. Crear ejecutables con build.py")
        print("   3. Probar ejecutables en diferentes sistemas")
        print("   4. Crear release en GitHub")
        print("   5. Actualizar documentación si es necesario")
    else:
        print("❌ Algunos checks críticos fallaron")
        print("🔧 Corrige los errores antes del release")
    
    return all_checks_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
