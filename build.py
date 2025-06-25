#!/usr/bin/env python3
"""
Constructor Universal de Ejecutables
Funciona en Windows, macOS y Linux
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def print_header():
    """Mostrar header del constructor"""
    system = platform.system()
    print("🏗️ SL y TP Automático - Constructor Universal")
    print("=" * 50)
    print(f"🖥️  Sistema: {system} {platform.release()}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print()

def check_requirements():
    """Verificar requisitos"""
    print("📋 Verificando requisitos...")
    
    # Verificar PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller no encontrado")
        print("💡 Instalando PyInstaller...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
        print("✅ PyInstaller instalado")
    
    # Verificar dependencias principales
    deps = ['PySide6', 'pybit', 'requests']
    for dep in deps:
        try:
            __import__(dep)
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep} no encontrado")
            print(f"💡 Instala con: pip install {dep}")
            return False
    
    return True

def clean_build():
    """Limpiar builds anteriores"""
    print("\n🧹 Limpiando builds anteriores...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['*.spec']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   🗑️ Eliminado: {dir_name}/")
    
    # Limpiar archivos .spec
    for spec_file in Path('.').glob('*.spec'):
        spec_file.unlink()
        print(f"   🗑️ Eliminado: {spec_file}")

def get_platform_config():
    """Obtener configuración específica de la plataforma"""
    system = platform.system().lower()
    
    config = {
        'name': 'SL-TP-Automatico',
        'script': 'pyside_trading_gui.py',
        'options': [
            '--onefile',
            '--windowed',
            '--clean',
            '--noconfirm',
        ]
    }
    
    # Datos adicionales
    config['add_data'] = []
    if os.path.exists('README.md'):
        separator = ';' if system == 'windows' else ':'
        config['add_data'].append(f'README.md{separator}.')
    
    # Imports ocultos
    config['hidden_imports'] = [
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'PySide6.QtNetwork',
        'pybit',
        'requests'
    ]

    # Módulos a excluir (problemáticos o innecesarios)
    config['excludes'] = [
        'PySide6.QtWebEngine',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.Qt3DCore',
        'PySide6.Qt3DRender',
        'PySide6.QtQuick',
        'PySide6.QtQml',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtCharts',
        'PySide6.QtDataVisualization',
        'matplotlib',
        'numpy',
        'scipy'
    ]
    
    # Configuración específica por plataforma
    if system == 'windows':
        if os.path.exists('icon.ico'):
            config['options'].append('--icon=icon.ico')
            
    elif system == 'darwin':  # macOS
        if os.path.exists('icon.icns'):
            config['options'].append('--icon=icon.icns')
        config['options'].append('--osx-bundle-identifier=com.codavidgarcia.sl-tp-automatico')
        
    elif system == 'linux':
        if os.path.exists('icon.png'):
            config['options'].append('--icon=icon.png')
    
    return config

def build_executable():
    """Construir el ejecutable"""
    print("\n🔨 Construyendo ejecutable...")
    print("   ⏳ Esto puede tomar varios minutos...")
    
    config = get_platform_config()
    
    # Construir comando
    cmd = ['pyinstaller']
    cmd.extend(config['options'])
    cmd.extend(['--name', config['name']])
    
    # Agregar datos
    for data in config['add_data']:
        cmd.extend(['--add-data', data])
    
    # Agregar imports ocultos
    for imp in config['hidden_imports']:
        cmd.extend(['--hidden-import', imp])

    # Excluir módulos problemáticos
    for exc in config.get('excludes', []):
        cmd.extend(['--exclude-module', exc])

    # Coleccionar solo los módulos necesarios de PySide6
    cmd.extend(['--collect-submodules', 'PySide6.QtCore'])
    cmd.extend(['--collect-submodules', 'PySide6.QtWidgets'])
    cmd.extend(['--collect-submodules', 'PySide6.QtGui'])
    
    # Script principal
    cmd.append(config['script'])
    
    print(f"📋 Comando: {' '.join(cmd)}")
    print()
    
    # Ejecutar construcción
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en la construcción:")
        print(e.stdout)
        print(e.stderr)
        return False

def show_results():
    """Mostrar resultados de la construcción"""
    system = platform.system().lower()
    
    if system == 'windows':
        exe_path = Path('dist/SL-TP-Automatico.exe')
        if exe_path.exists():
            size = exe_path.stat().st_size / (1024 * 1024)  # MB
            print(f"✅ Ejecutable creado: {exe_path}")
            print(f"📏 Tamaño: {size:.1f} MB")
            return str(exe_path)
    else:
        app_path = Path('dist/SL-TP-Automatico')
        if app_path.exists():
            # Obtener tamaño en Unix
            result = subprocess.run(['du', '-sh', str(app_path)], 
                                  capture_output=True, text=True)
            size = result.stdout.split()[0] if result.returncode == 0 else "Unknown"
            print(f"✅ Aplicación creada: {app_path}")
            print(f"📏 Tamaño: {size}")
            return str(app_path)
    
    return None

def test_executable(exe_path):
    """Probar el ejecutable"""
    print(f"\n🧪 ¿Deseas probar el ejecutable? [y/N]: ", end="")
    response = input().strip().lower()
    
    if response in ['y', 'yes', 'sí', 's']:
        print("🚀 Ejecutando...")
        try:
            if platform.system().lower() == 'darwin':
                subprocess.Popen(['open', exe_path])
            elif platform.system().lower() == 'windows':
                subprocess.Popen([exe_path])
            else:  # Linux
                subprocess.Popen([exe_path])
        except Exception as e:
            print(f"❌ Error ejecutando: {e}")

def main():
    """Función principal"""
    print_header()
    
    # Verificar requisitos
    if not check_requirements():
        print("\n❌ Faltan dependencias. Instálalas primero.")
        sys.exit(1)
    
    # Limpiar builds anteriores
    clean_build()
    
    # Construir ejecutable
    if not build_executable():
        print("\n❌ Error en la construcción")
        sys.exit(1)
    
    # Mostrar resultados
    exe_path = show_results()
    
    if exe_path:
        print("\n🎯 Para distribuir:")
        print(f"   📁 Copia el archivo: {exe_path}")
        print("   👥 Los usuarios pueden ejecutarlo directamente")
        print("   🐍 No necesitan Python instalado")
        
        # Probar ejecutable
        test_executable(exe_path)
    
    print("\n✅ ¡Proceso completado!")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Construcción cancelada por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)
