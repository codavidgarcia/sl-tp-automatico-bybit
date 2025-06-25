"""
Configuración avanzada para PyInstaller
Optimiza el proceso de construcción del ejecutable
"""

import os
import sys
import platform

def get_build_config():
    """Obtiene la configuración de build según la plataforma"""
    
    system = platform.system().lower()
    
    # Configuración base
    config = {
        'name': 'SL-TP-Automatico',
        'script': 'pyside_trading_gui.py',
        'onefile': True,
        'windowed': True,
        'clean': True,
        'noconfirm': True,
    }
    
    # Datos adicionales
    config['add_data'] = [
        ('README.md', '.'),
    ]
    
    # Imports ocultos necesarios
    config['hidden_imports'] = [
        'PySide6.QtCore',
        'PySide6.QtWidgets', 
        'PySide6.QtGui',
        'PySide6.QtNetwork',
        'pybit',
        'requests',
        'json',
        'threading',
        'queue',
        'time',
        'sys',
        'os'
    ]
    
    # Colecciones completas
    config['collect_all'] = [
        'PySide6',
    ]
    
    # Configuración específica por plataforma
    if system == 'windows':
        config['icon'] = 'icon.ico'
        config['version_file'] = 'version_info.txt'
        
    elif system == 'darwin':  # macOS
        config['icon'] = 'icon.icns'
        config['bundle_identifier'] = 'com.codavidgarcia.sl-tp-automatico'
        
    elif system == 'linux':
        config['icon'] = 'icon.png'
    
    return config

def build_command():
    """Genera el comando PyInstaller"""
    config = get_build_config()
    
    cmd = ['pyinstaller']
    
    # Opciones básicas
    if config.get('onefile'):
        cmd.append('--onefile')
    if config.get('windowed'):
        cmd.append('--windowed')
    if config.get('clean'):
        cmd.append('--clean')
    if config.get('noconfirm'):
        cmd.append('--noconfirm')
    
    # Nombre
    cmd.extend(['--name', config['name']])
    
    # Icono
    if config.get('icon') and os.path.exists(config['icon']):
        cmd.extend(['--icon', config['icon']])
    
    # Datos adicionales
    for src, dst in config.get('add_data', []):
        if os.path.exists(src):
            cmd.extend(['--add-data', f'{src}{os.pathsep}{dst}'])
    
    # Imports ocultos
    for imp in config.get('hidden_imports', []):
        cmd.extend(['--hidden-import', imp])
    
    # Colecciones
    for coll in config.get('collect_all', []):
        cmd.extend(['--collect-all', coll])
    
    # Configuración específica de macOS
    if platform.system().lower() == 'darwin':
        if config.get('bundle_identifier'):
            cmd.extend(['--osx-bundle-identifier', config['bundle_identifier']])
    
    # Archivo de versión para Windows
    if platform.system().lower() == 'windows':
        if config.get('version_file') and os.path.exists(config['version_file']):
            cmd.extend(['--version-file', config['version_file']])
    
    # Script principal
    cmd.append(config['script'])
    
    return cmd

if __name__ == '__main__':
    """Ejecutar construcción"""
    import subprocess
    
    print(f"🏗️ Construyendo para {platform.system()}")
    print("=" * 50)
    
    cmd = build_command()
    print(f"📋 Comando: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True)
        print("✅ ¡Construcción exitosa!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en la construcción: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ PyInstaller no encontrado. Instala con: pip install pyinstaller")
        sys.exit(1)
