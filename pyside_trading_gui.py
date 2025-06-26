"""
Professional Trading Bot GUI using PySide6
Modern, beautiful, and fully functional interface
"""

import sys
import os
import threading
import queue
import time
from typing import Optional

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# PySide6 imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QPushButton, QCheckBox,
    QTextEdit, QGroupBox, QFormLayout, QGridLayout, QSpacerItem, QSizePolicy,
    QMessageBox, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QFont, QPalette, QColor, QIcon

# Import trading modules
try:
    from trading_engine import TradingEngine
    from config_manager import ConfigManager
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import trading modules: {e}")
    MODULES_AVAILABLE = False


class ConnectionTestWorker(QObject):
    """Worker for testing API connection in background"""
    finished = Signal(bool, str)
    
    def __init__(self, api_key: str, api_secret: str):
        super().__init__()
        self.api_key = api_key
        self.api_secret = api_secret
    
    def run(self):
        """Test connection"""
        try:
            engine = TradingEngine(self.api_key, self.api_secret, False)  # Always use mainnet
            success = engine.initialize_session()
            message = "¡Conexión exitosa!" if success else "¡Conexión fallida!"
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, f"Error de conexión: {e}")


class TradingWorker(QObject):
    """Worker for trading operations"""
    finished = Signal(bool, str)
    log_message = Signal(str)
    
    def __init__(self, config_manager, symbol: str, sl_enabled: bool, sl_amount: float, 
                 tp_enabled: bool, tp_percentage: float):
        super().__init__()
        self.config_manager = config_manager
        self.symbol = symbol
        self.sl_enabled = sl_enabled
        self.sl_amount = sl_amount
        self.tp_enabled = tp_enabled
        self.tp_percentage = tp_percentage
        self.trading_engine = None
    
    def start_trading(self):
        """Start trading"""
        try:
            self.trading_engine = TradingEngine(
                self.config_manager.get_api_key(),
                self.config_manager.get_api_secret(),
                False  # Always use mainnet
            )
            
            # Set up log forwarding
            self.trading_engine.log_queue = queue.Queue()
            
            success = self.trading_engine.start_trading(
                self.symbol, self.sl_enabled, self.sl_amount,
                self.tp_enabled, self.tp_percentage
            )
            
            if success:
                self.finished.emit(True, "Trading started successfully")
                # Start log monitoring
                self.monitor_logs()
            else:
                self.finished.emit(False, "Failed to start trading")
                
        except Exception as e:
            self.finished.emit(False, f"Error starting trading: {e}")
    
    def monitor_logs(self):
        """Monitor logs from trading engine"""
        if self.trading_engine and self.trading_engine.log_queue:
            try:
                while True:
                    try:
                        message = self.trading_engine.log_queue.get_nowait()
                        self.log_message.emit(message)
                    except queue.Empty:
                        break
            except Exception as e:
                print(f"Log monitoring error: {e}")
    
    def stop_trading(self):
        """Stop trading"""
        if self.trading_engine:
            self.trading_engine.stop_trading()

    def update_sl_amount(self, new_amount: float):
        """Update SL amount in real-time"""
        self.sl_amount = new_amount
        if self.trading_engine and hasattr(self.trading_engine, 'update_sl_amount'):
            self.trading_engine.update_sl_amount(new_amount)

    def update_tp_percentage(self, new_percentage: float):
        """Update TP percentage in real-time"""
        self.tp_percentage = new_percentage
        if self.trading_engine and hasattr(self.trading_engine, 'update_tp_percentage'):
            self.trading_engine.update_tp_percentage(new_percentage)

    def update_sl_enabled(self, enabled: bool):
        """Update SL enabled state in real-time"""
        self.sl_enabled = enabled
        if self.trading_engine and hasattr(self.trading_engine, 'update_sl_enabled'):
            self.trading_engine.update_sl_enabled(enabled)

    def update_tp_enabled(self, enabled: bool):
        """Update TP enabled state in real-time"""
        self.tp_enabled = enabled
        if self.trading_engine and hasattr(self.trading_engine, 'update_tp_enabled'):
            self.trading_engine.update_tp_enabled(enabled)


class PySideTradingGUI(QMainWindow):
    """Professional Trading Bot GUI using PySide6"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize components
        if MODULES_AVAILABLE:
            self.config_manager = ConfigManager()
        else:
            self.config_manager = None
        
        self.trading_worker = None
        self.trading_thread = None
        self.trading_engine = None
        self.is_trading_active = False  # Track actual trading state

        # Thread management
        self.connection_worker = None
        self.connection_thread = None
        self.active_threads = []  # Track all active threads

        # Debounce timers for input fields to prevent UI blocking
        self.sl_debounce_timer = QTimer()
        self.sl_debounce_timer.setSingleShot(True)
        self.sl_debounce_timer.timeout.connect(self.apply_sl_change)

        self.tp_debounce_timer = QTimer()
        self.tp_debounce_timer.setSingleShot(True)
        self.tp_debounce_timer.timeout.connect(self.apply_tp_change)
        
        # Setup UI
        self.setup_ui()
        self.setup_styles()

        # Setup log timer
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.update_logs)
        self.log_timer.start(100)  # Update every 100ms

        # Load saved settings after UI is fully created
        self.load_saved_settings()

        self.add_log("🚀 Application started successfully")

        print("✅ PySide6 GUI initialized successfully!")

    def closeEvent(self, event):
        """Handle application close event - clean up threads"""
        print("🔄 Cerrando aplicación y limpiando recursos...")

        # Stop trading if active
        if self.is_trading_active:
            self.stop_trading()

        # Clean up connection thread
        if self.connection_thread and self.connection_thread.isRunning():
            self.connection_thread.quit()
            self.connection_thread.wait(3000)  # Wait up to 3 seconds

        # Clean up trading thread
        if self.trading_thread and self.trading_thread.isRunning():
            self.trading_thread.quit()
            self.trading_thread.wait(3000)  # Wait up to 3 seconds

        # Clean up any other active threads
        for thread in self.active_threads:
            if thread and thread.isRunning():
                thread.quit()
                thread.wait(1000)  # Wait up to 1 second each

        # Stop trading engine
        if self.trading_engine and hasattr(self.trading_engine, 'stop_trading'):
            self.trading_engine.stop_trading()

        print("✅ Recursos limpiados correctamente")
        event.accept()

    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("🚀 SL y TP Automático en Bybit")
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumSize(800, 500)  # Tamaño mínimo
        self.resize(1000, 700)  # Tamaño inicial redimensionable
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        self.create_header(main_layout)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Create tabs in correct order
        print("Creando pestaña de Configuración API...")
        self.create_config_tab()
        print("Creando pestaña de Trading y Posiciones...")
        self.create_trading_tab()
        print("Creando pestaña de Monitor en Vivo...")
        self.create_monitor_tab()
        print("Creando pestaña de Acerca de...")
        self.create_about_tab()

        # Connect tab change signal for auto-refresh
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # Ensure config tab is selected by default
        self.tab_widget.setCurrentIndex(0)
        
        # Status bar with dynamic connection status
        self.update_connection_status()

    def on_tab_changed(self, index):
        """Handle tab change - auto refresh trading tab"""
        tab_text = self.tab_widget.tabText(index)
        if "Trading y Posiciones" in tab_text:
            # Auto-refresh positions when switching to trading tab
            if hasattr(self, 'refresh_positions_btn'):
                self.refresh_positions()

    def update_automation_status(self):
        """Update compact status indicators - requires BOTH checkbox AND trading active"""
        if not hasattr(self, 'sl_status_circle') or not hasattr(self, 'tp_status_circle'):
            return

        # Update SL status indicator - green only if checkbox checked AND trading active
        sl_active = self.sl_checkbox.isChecked() and self.is_trading_active
        self.sl_status_circle.setText("🟢" if sl_active else "🔴")

        # Update TP status indicator - green only if checkbox checked AND trading active
        tp_active = self.tp_checkbox.isChecked() and self.is_trading_active
        self.tp_status_circle.setText("🟢" if tp_active else "🔴")

    def update_connection_status(self):
        """Update status bar with real-time API connection status"""
        if not MODULES_AVAILABLE:
            self.statusBar().showMessage("Revisa tu configuración de API")
            return

        if not self.config_manager or not self.config_manager.has_valid_credentials():
            self.statusBar().showMessage("Desconectado - Configure API")
            return

        # Check if we have valid credentials and show connected
        if self.config_manager.has_valid_credentials():
            self.statusBar().showMessage("Conectado")
        else:
            self.statusBar().showMessage("Desconectado")
    
    def create_header(self, parent_layout):
        """Create header section"""
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border: none;
            }
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(30, 20, 30, 20)
        
        # Title
        title = QLabel("🚀 SL - TP Automático para Bybit")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                background: transparent;
            }
        """)
        header_layout.addWidget(title)
        
        # Spacer
        header_layout.addStretch()
        
        # Status
        self.status_label = QLabel("Listo")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #2ecc71;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }
        """)
        header_layout.addWidget(self.status_label)
        
        parent_layout.addWidget(header)
    
    def create_config_tab(self):
        """Create API configuration tab"""
        print("Starting to create config tab...")
        config_widget = QWidget()
        tab_index = self.tab_widget.addTab(config_widget, "🔑 Configuración API")
        print(f"Config tab added at index: {tab_index}")
        
        # Main layout for config tab
        layout = QVBoxLayout(config_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Configuración de API Bybit")
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title)
        
        # API Configuration Group - Optimized layout
        api_group = QGroupBox("Credenciales de API")
        api_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #34495e;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                padding-bottom: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

        # Use a grid layout for better space optimization
        api_layout = QGridLayout(api_group)
        api_layout.setSpacing(10)
        api_layout.setContentsMargins(15, 20, 15, 15)
        
        # API Key - Row 0
        api_key_label = QLabel("Clave API:")
        api_key_label.setStyleSheet("font-weight: bold; color: #34495e; font-size: 12px;")
        api_layout.addWidget(api_key_label, 0, 0)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                font-size: 12px;
                font-family: 'Courier New', monospace;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        api_layout.addWidget(self.api_key_input, 0, 1)

        self.show_api_key_btn = QPushButton("👁️")
        self.show_api_key_btn.setFixedSize(35, 35)
        self.show_api_key_btn.setStyleSheet("""
            QPushButton {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: #ecf0f1;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d5dbdb;
            }
        """)
        self.show_api_key_btn.clicked.connect(lambda: self.toggle_password(self.api_key_input))
        api_layout.addWidget(self.show_api_key_btn, 0, 2)

        # API Secret - Row 1
        api_secret_label = QLabel("Secreto API:")
        api_secret_label.setStyleSheet("font-weight: bold; color: #34495e; font-size: 12px;")
        api_layout.addWidget(api_secret_label, 1, 0)

        self.api_secret_input = QLineEdit()
        self.api_secret_input.setEchoMode(QLineEdit.Password)
        self.api_secret_input.setStyleSheet(self.api_key_input.styleSheet())
        api_layout.addWidget(self.api_secret_input, 1, 1)

        self.show_api_secret_btn = QPushButton("👁️")
        self.show_api_secret_btn.setFixedSize(35, 35)
        self.show_api_secret_btn.setStyleSheet(self.show_api_key_btn.styleSheet())
        self.show_api_secret_btn.clicked.connect(lambda: self.toggle_password(self.api_secret_input))
        api_layout.addWidget(self.show_api_secret_btn, 1, 2)

        # Set column stretch to make input fields expand
        api_layout.setColumnStretch(1, 1)  # Input fields take most space
        api_layout.setColumnMinimumWidth(0, 80)  # Label column minimum width
        

        
        layout.addWidget(api_group)
        
        # Buttons
        button_layout = QHBoxLayout()

        self.save_btn = QPushButton("💾 Guardar Credenciales")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                min-width: 180px;
            }
            QPushButton:hover {
                background-color: #2980b9;
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        self.save_btn.clicked.connect(self.save_credentials)
        button_layout.addWidget(self.save_btn)

        self.test_btn = QPushButton("🔍 Probar Conexión")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                min-width: 160px;
            }
            QPushButton:hover {
                background-color: #229954;
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_btn)

        # Clear credentials button
        self.clear_btn = QPushButton("🗑️ Limpiar Credenciales")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                min-width: 160px;
            }
            QPushButton:hover {
                background-color: #c0392b;
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_credentials)
        button_layout.addWidget(self.clear_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Status indicator
        self.api_status_label = QLabel("⚪ Sin credenciales guardadas")
        self.api_status_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 12px;
                font-weight: bold;
                margin-top: 10px;
                padding: 8px 12px;
                background-color: #ecf0f1;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.api_status_label)
        
        # Instructions with Security Note in two columns
        instructions_group = QGroupBox("📋 Instrucciones de Configuración")
        instructions_group.setStyleSheet(api_group.styleSheet())

        # Horizontal layout for two columns
        instructions_main_layout = QHBoxLayout(instructions_group)
        instructions_main_layout.setSpacing(20)

        # Left column - Configuration steps
        config_layout = QVBoxLayout()
        config_title = QLabel("🔧 Configuración:")
        config_title.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-size: 12px;
                font-weight: bold;
                margin-bottom: 5px;
            }
        """)
        config_layout.addWidget(config_title)

        instructions = [
            "1. Visita bybit.com → Gestión de API",
            "2. Crea una clave API con permisos de 'Trading de Futuros'",
            "3. Ingresa tu Clave API y Secreto aquí arriba",
            "4. Guarda y prueba tu conexión"
        ]

        for instruction in instructions:
            label = QLabel(instruction)
            label.setStyleSheet("""
                QLabel {
                    color: #34495e;
                    font-size: 11px;
                    margin: 2px 0;
                }
            """)
            config_layout.addWidget(label)

        # Right column - Security note
        security_layout = QVBoxLayout()
        security_title = QLabel("🔒 Seguridad:")
        security_title.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-size: 12px;
                font-weight: bold;
                margin-bottom: 5px;
            }
        """)
        security_layout.addWidget(security_title)

        security_notes = [
            "• Tus credenciales se guardan SOLO en tu computadora",
            "• Archivo: config.json en la carpeta de la aplicación",
            "• NO se envían a servidores externos",
            "• Conexión directa y segura con Bybit API"
        ]

        for note in security_notes:
            label = QLabel(note)
            label.setStyleSheet("""
                QLabel {
                    color: #27ae60;
                    font-size: 11px;
                    margin: 2px 0;
                    font-weight: 500;
                }
            """)
            security_layout.addWidget(label)

        # Add columns to main layout
        instructions_main_layout.addLayout(config_layout)
        instructions_main_layout.addLayout(security_layout)

        layout.addWidget(instructions_group)
        layout.addStretch()
    
    def create_trading_tab(self):
        """Create trading configuration tab"""
        trading_widget = QWidget()
        self.tab_widget.addTab(trading_widget, "📈 Trading y Posiciones")
        
        layout = QVBoxLayout(trading_widget)
        layout.setContentsMargins(20, 20, 20, 20)  # Reduced margins for better space usage
        layout.setSpacing(15)  # Consistent spacing
        
        # Title with controls in same line
        title_layout = QHBoxLayout()
        title_layout.setSpacing(15)

        title = QLabel("Trading y Posiciones")
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)
        title_layout.addWidget(title)
        title_layout.addStretch()

        # Move refresh controls to title line
        self.refresh_positions_btn = QPushButton("🔄 Actualizar")
        self.refresh_positions_btn.setStyleSheet("""
            QPushButton {
                background-color: #4299e1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #3182ce;
            }
        """)
        self.refresh_positions_btn.clicked.connect(self.refresh_positions)
        title_layout.addWidget(self.refresh_positions_btn)

        self.auto_refresh_checkbox = QCheckBox("Auto")
        self.auto_refresh_checkbox.setChecked(True)  # Por defecto activado
        self.auto_refresh_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 12px;
                color: #4a5568;
                font-weight: 500;
                margin-left: 8px;
            }
        """)
        self.auto_refresh_checkbox.stateChanged.connect(self.toggle_auto_refresh)
        title_layout.addWidget(self.auto_refresh_checkbox)

        # Compact status indicators - modern design
        title_layout.addWidget(QLabel("  |  "))  # Visual separator

        # SL Status Indicator
        self.sl_status_label = QLabel("SL")
        self.sl_status_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: bold;
                color: #4a5568;
                margin: 0px 2px;
            }
        """)
        title_layout.addWidget(self.sl_status_label)

        self.sl_status_circle = QLabel("🔴")
        self.sl_status_circle.setStyleSheet("""
            QLabel {
                font-size: 12px;
                margin: 0px 8px 0px 2px;
            }
        """)
        title_layout.addWidget(self.sl_status_circle)

        # TP Status Indicator
        self.tp_status_label = QLabel("TP")
        self.tp_status_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: bold;
                color: #4a5568;
                margin: 0px 2px;
            }
        """)
        title_layout.addWidget(self.tp_status_label)

        self.tp_status_circle = QLabel("🔴")
        self.tp_status_circle.setStyleSheet("""
            QLabel {
                font-size: 12px;
                margin: 0px 2px;
            }
        """)
        title_layout.addWidget(self.tp_status_circle)

        layout.addLayout(title_layout)

        # Positions Section (Top)
        self.create_positions_section(layout)
        
        # Consolidated Trading Controls - Compact Responsive Design
        trading_controls_group = QGroupBox("⚡ Controles de Trading")
        trading_controls_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                border: 3px solid #34495e;
                border-radius: 12px;
                margin-top: 10px;
                padding-top: 12px;
                padding-bottom: 12px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                background-color: #ffffff;
            }
        """)

        # Set responsive size policy
        trading_controls_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Simple horizontal layout for trading controls
        main_controls_layout = QHBoxLayout(trading_controls_group)
        main_controls_layout.setSpacing(40)
        main_controls_layout.setContentsMargins(30, 25, 30, 25)

        # Ticker section - Simple design
        ticker_layout = QVBoxLayout()
        ticker_layout.setSpacing(8)

        ticker_label = QLabel("📊 Ticker")
        ticker_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        ticker_layout.addWidget(ticker_label)

        ticker_input_layout = QHBoxLayout()
        ticker_input_layout.setSpacing(8)

        self.symbol_input = QLineEdit("BTC")
        self.symbol_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 15px;
                border: 2px solid #3498db;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                min-width: 100px;
                background-color: #ffffff;
                color: #1a202c;
            }
            QLineEdit:focus {
                border-color: #2980b9;
            }
        """)
        ticker_input_layout.addWidget(self.symbol_input)

        usdt_label = QLabel("USDT")
        usdt_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #7f8c8d;
            }
        """)
        ticker_input_layout.addWidget(usdt_label)

        ticker_layout.addLayout(ticker_input_layout)
        main_controls_layout.addLayout(ticker_layout)

        # SL section - Simple design
        sl_layout = QVBoxLayout()
        sl_layout.setSpacing(8)

        # Header with checkbox
        sl_header_layout = QHBoxLayout()
        sl_header_layout.setSpacing(10)

        self.sl_checkbox = QCheckBox("🛡️ SL Automático")
        self.sl_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 16px;
                font-weight: bold;
                color: #c0392b;
                background-color: #fdf2f2;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #e74c3c;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #e74c3c;
                border-radius: 3px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #e74c3c;
                border-color: #c0392b;
            }
        """)
        self.sl_checkbox.stateChanged.connect(self.update_automation_status)
        self.sl_checkbox.stateChanged.connect(self.on_sl_checkbox_changed)
        sl_header_layout.addWidget(self.sl_checkbox)

        # SL Order Status Indicator
        self.sl_order_indicator = QLabel("●")
        self.sl_order_indicator.setStyleSheet("""
            QLabel {
                color: #95a5a6;
                font-size: 12px;
                font-weight: bold;
                margin-left: 5px;
            }
        """)
        self.sl_order_indicator.setToolTip("Estado de la orden SL en Bybit")
        sl_header_layout.addWidget(self.sl_order_indicator)

        sl_header_layout.addStretch()
        sl_layout.addLayout(sl_header_layout)

        # Input section
        sl_input_layout = QHBoxLayout()
        sl_input_layout.setSpacing(8)

        perdida_label = QLabel("Pérdida:")
        perdida_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        sl_input_layout.addWidget(perdida_label)

        self.sl_amount_input = QLineEdit("10.0")
        self.sl_amount_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 15px;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                min-width: 80px;
                font-size: 16px;
                font-weight: bold;
                background-color: #ffffff;
                color: #1a202c;
            }
            QLineEdit:focus {
                border-color: #c0392b;
            }
        """)
        # Connect to auto-update function
        self.sl_amount_input.textChanged.connect(self.on_sl_value_changed)
        sl_input_layout.addWidget(self.sl_amount_input)

        usdt_label = QLabel("USDT")
        usdt_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #7f8c8d;
            }
        """)
        sl_input_layout.addWidget(usdt_label)

        sl_layout.addLayout(sl_input_layout)
        main_controls_layout.addLayout(sl_layout)

        # TP section - Simple design
        tp_layout = QVBoxLayout()
        tp_layout.setSpacing(8)

        # Header with checkbox
        tp_header_layout = QHBoxLayout()
        tp_header_layout.setSpacing(10)

        self.tp_checkbox = QCheckBox("💰 TP Automático")
        self.tp_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 16px;
                font-weight: bold;
                color: #1e8449;
                background-color: #f0f9f4;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #27ae60;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #27ae60;
                border-radius: 3px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #27ae60;
                border-color: #1e8449;
            }
        """)
        self.tp_checkbox.stateChanged.connect(self.update_automation_status)
        self.tp_checkbox.stateChanged.connect(self.on_tp_checkbox_changed)
        tp_header_layout.addWidget(self.tp_checkbox)

        # TP Order Status Indicator
        self.tp_order_indicator = QLabel("●")
        self.tp_order_indicator.setStyleSheet("""
            QLabel {
                color: #95a5a6;
                font-size: 12px;
                font-weight: bold;
                margin-left: 5px;
            }
        """)
        self.tp_order_indicator.setToolTip("Estado de la orden TP en Bybit")
        tp_header_layout.addWidget(self.tp_order_indicator)

        tp_header_layout.addStretch()
        tp_layout.addLayout(tp_header_layout)

        # Input section
        tp_input_layout = QHBoxLayout()
        tp_input_layout.setSpacing(8)

        ganancia_label = QLabel("Ganancia:")
        ganancia_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        tp_input_layout.addWidget(ganancia_label)

        self.tp_percentage_input = QLineEdit("2.0")
        self.tp_percentage_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 15px;
                border: 2px solid #27ae60;
                border-radius: 8px;
                min-width: 80px;
                font-size: 16px;
                font-weight: bold;
                background-color: #ffffff;
                color: #1a202c;
            }
            QLineEdit:focus {
                border-color: #1e8449;
            }
        """)
        # Connect to auto-update function
        self.tp_percentage_input.textChanged.connect(self.on_tp_value_changed)
        tp_input_layout.addWidget(self.tp_percentage_input)

        percent_label = QLabel("%")
        percent_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #7f8c8d;
            }
        """)
        tp_input_layout.addWidget(percent_label)

        tp_layout.addLayout(tp_input_layout)
        main_controls_layout.addLayout(tp_layout)

        # Add the consolidated group to the main layout
        layout.addWidget(trading_controls_group)

        # Control Buttons
        control_layout = QHBoxLayout()

        self.start_btn = QPushButton("🚀 Iniciar SL / TP Automáticos")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.start_btn.clicked.connect(self.start_trading)
        control_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏸️ Pausar SL / TP Automáticos")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_trading)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)

        control_layout.addStretch()
        layout.addLayout(control_layout)
        layout.addStretch()

        # Initialize compact status indicators
        self.update_automation_status()
        self.update_order_indicators()

    def on_sl_value_changed(self, text):
        """Handle SL value change - use debounce to prevent UI blocking"""
        if not self.is_trading_active or not self.trading_worker:
            return

        # Store the current text for later processing
        self.pending_sl_value = text

        # Restart the debounce timer (500ms delay)
        self.sl_debounce_timer.stop()
        self.sl_debounce_timer.start(500)

    def apply_sl_change(self):
        """Apply SL change after debounce delay"""
        if not hasattr(self, 'pending_sl_value'):
            return

        text = self.pending_sl_value
        try:
            sl_amount = float(text) if text else 0.0
            if sl_amount > 0 and self.sl_checkbox.isChecked():
                # Update SL in real-time
                if hasattr(self.trading_worker, 'update_sl_amount'):
                    self.trading_worker.update_sl_amount(sl_amount)
                    self.add_log(f"🛡️ SL actualizado en vivo: ${sl_amount:.2f} USDT")
        except ValueError:
            pass  # Invalid number, ignore

    def on_tp_value_changed(self, text):
        """Handle TP value change - use debounce to prevent UI blocking"""
        if not self.is_trading_active or not self.trading_worker:
            return

        # Store the current text for later processing
        self.pending_tp_value = text

        # Restart the debounce timer (500ms delay)
        self.tp_debounce_timer.stop()
        self.tp_debounce_timer.start(500)

    def apply_tp_change(self):
        """Apply TP change after debounce delay"""
        if not hasattr(self, 'pending_tp_value'):
            return

        text = self.pending_tp_value
        try:
            tp_percentage = float(text) if text else 0.0
            if tp_percentage > 0 and self.tp_checkbox.isChecked():
                # Update TP in real-time
                if hasattr(self.trading_worker, 'update_tp_percentage'):
                    self.trading_worker.update_tp_percentage(tp_percentage)
                    self.add_log(f"💰 TP actualizado en vivo: {tp_percentage:.2f}%")
        except ValueError:
            pass  # Invalid number, ignore

    def on_sl_checkbox_changed(self, state):
        """Handle SL checkbox change - enable/disable SL in real-time"""
        if not self.is_trading_active or not self.trading_worker:
            return

        enabled = state == 2  # Qt.Checked
        if hasattr(self.trading_worker, 'update_sl_enabled'):
            self.trading_worker.update_sl_enabled(enabled)
            status = "activado" if enabled else "desactivado"
            self.add_log(f"🛡️ SL {status} en vivo")

        # Update visual indicator
        self.update_order_indicators()

    def on_tp_checkbox_changed(self, state):
        """Handle TP checkbox change - enable/disable TP in real-time"""
        if not self.is_trading_active or not self.trading_worker:
            return

        enabled = state == 2  # Qt.Checked
        if hasattr(self.trading_worker, 'update_tp_enabled'):
            self.trading_worker.update_tp_enabled(enabled)
            status = "activado" if enabled else "desactivado"
            self.add_log(f"💰 TP {status} en vivo")

        # Update visual indicator
        self.update_order_indicators()

    def update_order_indicators(self):
        """Update visual indicators for order status"""
        # SL Indicator
        if self.is_trading_active and self.sl_checkbox.isChecked():
            self.sl_order_indicator.setStyleSheet("""
                QLabel {
                    color: #e74c3c;
                    font-size: 12px;
                    font-weight: bold;
                    margin-left: 5px;
                }
            """)
            self.sl_order_indicator.setToolTip("🛡️ Orden SL activa en Bybit")
        else:
            self.sl_order_indicator.setStyleSheet("""
                QLabel {
                    color: #95a5a6;
                    font-size: 12px;
                    font-weight: bold;
                    margin-left: 5px;
                }
            """)
            self.sl_order_indicator.setToolTip("⚪ SL inactivo")

        # TP Indicator
        if self.is_trading_active and self.tp_checkbox.isChecked():
            self.tp_order_indicator.setStyleSheet("""
                QLabel {
                    color: #27ae60;
                    font-size: 12px;
                    font-weight: bold;
                    margin-left: 5px;
                }
            """)
            self.tp_order_indicator.setToolTip("💰 Orden TP activa en Bybit")
        else:
            self.tp_order_indicator.setStyleSheet("""
                QLabel {
                    color: #95a5a6;
                    font-size: 12px;
                    font-weight: bold;
                    margin-left: 5px;
                }
            """)
            self.tp_order_indicator.setToolTip("⚪ TP inactivo")

    def create_positions_section(self, parent_layout):
        """Create compact positions section optimized for vertical space"""
        # Compact container - CONSISTENT STYLING with trading controls
        positions_container = QGroupBox("📊 Posiciones")
        positions_container.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                border: 1px solid #34495e;
                border-radius: 8px;
                margin-top: 5px;
                padding-top: 2px;
                padding-bottom: 2px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                background-color: #ffffff;
            }
        """)

        main_layout = QVBoxLayout(positions_container)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # No header needed - controls moved to main title

        # PRIORITY: Summary cards - ALWAYS VISIBLE
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(6)
        cards_layout.setContentsMargins(0, 0, 0, 0)

        # Create PRIORITY cards - these MUST be visible
        self.total_positions_card = self.create_compact_card("Total", "0", "#4299e1")
        self.total_pnl_card = self.create_compact_card("PnL", "$0.00", "#48bb78")
        self.total_value_card = self.create_compact_card("Valor", "$0.00", "#9f7aea")

        cards_layout.addWidget(self.total_positions_card)
        cards_layout.addWidget(self.total_pnl_card)
        cards_layout.addWidget(self.total_value_card)

        main_layout.addLayout(cards_layout)

        # SECONDARY: Minimal table - can be hidden if needed
        self.create_compact_table(main_layout)

        parent_layout.addWidget(positions_container)

        # Auto-refresh timer
        self.positions_refresh_timer = QTimer()
        self.positions_refresh_timer.timeout.connect(self.refresh_positions)

        # Start auto-refresh by default since checkbox is checked by default
        self.positions_refresh_timer.start(5000)  # 5 seconds




    def create_monitor_tab(self):
        """Create monitoring tab"""
        monitor_widget = QWidget()
        self.tab_widget.addTab(monitor_widget, "📊 Monitor en Vivo")

        layout = QVBoxLayout(monitor_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Title
        title = QLabel("Monitor de Trading en Vivo")
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title)

        # Log header
        log_header_layout = QHBoxLayout()

        log_title = QLabel("📋 Registro de Actividad")
        log_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        log_header_layout.addWidget(log_title)
        log_header_layout.addStretch()

        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        clear_btn.clicked.connect(self.clear_log)
        log_header_layout.addWidget(clear_btn)

        layout.addLayout(log_header_layout)

        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ff41;
                border: 2px solid #34495e;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.log_display)





    def create_compact_card(self, title: str, value: str, color: str):
        """Create clean single-container card matching trading controls style"""
        # Single clean container - NO nested boxes
        card = QLabel(f"{title}: {value}")
        card.setStyleSheet(f"""
            QLabel {{
                padding: 12px 15px;
                border: 2px solid {color};
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                min-width: 120px;
                min-height: 50px;
                max-height: 50px;
                background-color: #ffffff;
                color: #1a202c;
                margin: 0px;
            }}
            QLabel:hover {{
                background-color: #f7fafc;
                border-color: {color};
            }}
        """)

        # FIXED size policy - NEVER shrinks
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setMinimumSize(120, 50)
        card.setMaximumSize(16777215, 50)
        card.setWordWrap(False)
        card.setAlignment(Qt.AlignCenter)

        # Store reference for updates - update the entire text
        setattr(card, 'title', title)
        setattr(card, 'update_value', lambda val: card.setText(f"{title}: {val}"))

        return card

    def create_compact_table(self, parent_layout):
        """Create MINIMAL table - secondary priority to cards"""
        from PySide6.QtWidgets import QTableWidget, QHeaderView

        self.positions_table = QTableWidget()
        # MINIMAL height - cards are priority
        self.positions_table.setMinimumHeight(80)
        self.positions_table.setMaximumHeight(150)  # Much smaller max
        self.positions_table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                gridline-color: #e2e8f0;
                font-size: 11px;
                font-weight: 500;
                selection-background-color: #4299e1;
                color: #1a202c;
            }
            QTableWidget::item {
                padding: 6px 4px;
                border-bottom: 1px solid #e2e8f0;
                color: #1a202c;
                background-color: #ffffff;
                min-height: 16px;
                font-weight: 500;
            }
            QTableWidget::item:selected {
                background-color: #4299e1;
                color: #ffffff;
                font-weight: 600;
            }
            QTableWidget::item:hover {
                background-color: #f7fafc;
                color: #1a202c;
            }
            QTableWidget::item:alternate {
                background-color: #f8f9fa;
                color: #1a202c;
            }
            QHeaderView::section {
                background-color: #2d3748;
                color: #ffffff;
                padding: 6px 4px;
                border: none;
                border-right: 1px solid #4a5568;
                font-weight: 700;
                font-size: 10px;
                text-transform: uppercase;
            }
            QHeaderView::section:last {
                border-right: none;
            }
        """)

        # Headers with select button
        headers = ["TICKER", "LADO", "TAMAÑO", "PNL", "%", "ACCIÓN"]
        self.positions_table.setColumnCount(len(headers))
        self.positions_table.setHorizontalHeaderLabels(headers)

        # Configure responsive columns
        header = self.positions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.positions_table.setAlternatingRowColors(True)
        self.positions_table.setSelectionBehavior(QTableWidget.SelectRows)
        # MINIMAL size policy - shrinks to give space to cards
        self.positions_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        parent_layout.addWidget(self.positions_table)

    def create_summary_card(self, title: str, value: str, color: str):
        """Legacy method - redirects to compact card"""
        return self.create_compact_card(title, value, color)



    def refresh_positions(self):
        """Refresh positions data"""
        if not MODULES_AVAILABLE:
            QMessageBox.warning(self, "Warning", "Por favor agrega primero tus credenciales API para usar el SL/TP automático")
            return

        # Initialize trading engine if not available
        if not self.trading_engine:
            if not self.config_manager or not self.config_manager.has_valid_credentials():
                QMessageBox.warning(self, "Warning",
                    "Please configure and test API credentials first in the API Configuration tab")
                return

            try:
                self.trading_engine = TradingEngine(
                    self.config_manager.get_api_key(),
                    self.config_manager.get_api_secret(),
                    False  # Always use mainnet
                )
                # Initialize session manually after object creation
                if self.trading_engine.initialize_session():
                    self.add_log("🔧 Motor de trading inicializado para monitoreo de posiciones")
                else:
                    self.add_log("⚠️ Motor de trading creado pero sesión no inicializada")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to initialize trading engine: {e}")
                return

        try:
            self.refresh_positions_btn.setEnabled(False)
            self.refresh_positions_btn.setText("🔄 Actualizando...")

            # Get positions summary
            summary = self.trading_engine.get_positions_summary()

            # Update summary cards
            self.update_summary_cards(summary)

            # Update positions table
            self.update_positions_table(summary['positions'])

            self.add_log(f"📊 Posiciones actualizadas - {summary['total_positions']} posiciones activas")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al actualizar posiciones: {e}")
            self.add_log(f"❌ Error actualizando posiciones: {e}")
        finally:
            self.refresh_positions_btn.setEnabled(True)
            self.refresh_positions_btn.setText("🔄 Actualizar")

    def update_summary_cards(self, summary):
        """Update summary cards with latest data"""
        # Update total positions
        self.total_positions_card.update_value(str(summary['total_positions']))

        # Update total PnL with color coding
        total_pnl = summary['total_unrealized_pnl']
        pnl_text = f"${total_pnl:,.2f}"
        pnl_color = "#1a5f2e" if total_pnl >= 0 else "#7f1d1d"

        self.total_pnl_card.update_value(pnl_text)
        # Update PnL card color
        current_style = self.total_pnl_card.styleSheet()
        new_style = current_style.replace("color: #1a202c;", f"color: {pnl_color};")
        self.total_pnl_card.setStyleSheet(new_style)

        # Update total value
        total_value = summary['total_position_value']
        self.total_value_card.update_value(f"${total_value:,.2f}")

    def update_positions_table(self, positions):
        """Update table with auto-selection logic - PRIORITY: Cards visible"""
        from PySide6.QtWidgets import QTableWidgetItem, QPushButton
        from PySide6.QtGui import QColor

        self.positions_table.setRowCount(len(positions))

        # AUTO-SELECT: If only one position, set it as ticker automatically
        if len(positions) == 1:
            symbol = positions[0]['symbol']
            if hasattr(self, 'symbol_input'):
                self.symbol_input.setText(symbol)
                print(f"✅ Auto-selected ticker: {symbol}")

        for row, pos in enumerate(positions):
            # Symbol
            self.positions_table.setItem(row, 0, QTableWidgetItem(pos['symbol']))

            # Side with color coding - FIXED CONTRAST
            side_text = "Compra" if pos['side'] == 'Buy' else "Venta"
            side_item = QTableWidgetItem(side_text)
            if pos['side'] == 'Buy':
                side_item.setBackground(QColor("#e6f7ed"))
                side_item.setForeground(QColor("#1a5f2e"))  # Dark green text
            else:
                side_item.setBackground(QColor("#fef2f2"))
                side_item.setForeground(QColor("#7f1d1d"))  # Dark red text
            self.positions_table.setItem(row, 1, side_item)

            # Size
            self.positions_table.setItem(row, 2, QTableWidgetItem(f"{pos['size']:.4f}"))

            # PnL with color coding - FIXED CONTRAST
            pnl = pos['unrealized_pnl']
            pnl_item = QTableWidgetItem(f"${pnl:.2f}")
            if pnl >= 0:
                pnl_item.setForeground(QColor("#1a5f2e"))  # Dark green
            else:
                pnl_item.setForeground(QColor("#7f1d1d"))  # Dark red
            self.positions_table.setItem(row, 3, pnl_item)

            # PnL % calculation
            if pos['entry_price'] > 0 and pos['mark_price'] > 0:
                if pos['side'] == 'Buy':
                    pnl_pct = ((pos['mark_price'] - pos['entry_price']) / pos['entry_price']) * 100
                else:
                    pnl_pct = ((pos['entry_price'] - pos['mark_price']) / pos['entry_price']) * 100

                pnl_pct_item = QTableWidgetItem(f"{pnl_pct:.2f}%")
                if pnl_pct >= 0:
                    pnl_pct_item.setForeground(QColor("#1a5f2e"))  # Dark green
                else:
                    pnl_pct_item.setForeground(QColor("#7f1d1d"))  # Dark red
                self.positions_table.setItem(row, 4, pnl_pct_item)
            else:
                self.positions_table.setItem(row, 4, QTableWidgetItem("N/A"))

            # SELECT BUTTON: Only show if multiple positions
            if len(positions) > 1:
                select_btn = QPushButton("Seleccionar")
                select_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4299e1;
                        color: white;
                        border: none;
                        padding: 2px 4px;
                        border-radius: 3px;
                        font-size: 8px;
                        font-weight: 600;
                        min-height: 16px;
                    }
                    QPushButton:hover {
                        background-color: #3182ce;
                    }
                """)
                symbol = pos['symbol']
                select_btn.clicked.connect(lambda _, s=symbol: self.select_ticker(s))
                self.positions_table.setCellWidget(row, 5, select_btn)
            else:
                # Empty cell if only one position
                self.positions_table.setItem(row, 5, QTableWidgetItem(""))

    def select_ticker(self, symbol):
        """Select ticker from table button"""
        if hasattr(self, 'symbol_input'):
            self.symbol_input.setText(symbol)
            print(f"✅ Selected ticker from table: {symbol}")
        else:
            print(f"⚠️ Symbol input not found, cannot select: {symbol}")

    def toggle_auto_refresh(self, state):
        """Toggle auto-refresh for positions"""
        if state == 2:  # Checked
            self.positions_refresh_timer.start(5000)  # 5 seconds
            self.add_log("🔄 Auto-actualización activada para posiciones (intervalo 5s)")
        else:
            self.positions_refresh_timer.stop()
            self.add_log("⏸️ Auto-actualización desactivada para posiciones")

    def debug_positions(self):
        """Debug positions API response"""
        if not MODULES_AVAILABLE or not self.trading_engine:
            QMessageBox.warning(self, "Warning", "Motor de trading no disponible")
            return

        try:
            # Check if session is available
            if not self.trading_engine.session:
                self.add_log("❌ Sesión no inicializada, intentando inicializar...")
                if not self.trading_engine.initialize_session():
                    QMessageBox.critical(self, "Error", "No se pudo inicializar la sesión de trading")
                    return

            self.add_log("🔍 === DEBUG: Respuesta completa de API ===")

            # Check USDT positions
            usdt_response = self.trading_engine.session.get_positions(category="linear", settleCoin="USDT")
            self.add_log(f"USDT Positions - retCode: {usdt_response.get('retCode')}")

            total_positions = 0
            if usdt_response.get('retCode') == 0:
                usdt_positions = usdt_response['result']['list']
                self.add_log(f"USDT posiciones encontradas: {len(usdt_positions)}")
                total_positions += len(usdt_positions)

                for i, pos in enumerate(usdt_positions):
                    symbol = pos.get('symbol', 'Unknown')
                    size = pos.get('size', '0')
                    side = pos.get('side', 'None')
                    unrealized_pnl = pos.get('unrealisedPnl', '0')
                    position_value = pos.get('positionValue', '0')
                    position_idx = pos.get('positionIdx', '0')

                    self.add_log(f"USDT-{i+1}: {symbol} | Size: {size} | Side: {side} | PnL: {unrealized_pnl} | Value: {position_value} | Idx: {position_idx}")
            else:
                self.add_log(f"Error USDT API: {usdt_response.get('retMsg', 'Error desconocido')}")

            # Check USDC positions
            try:
                usdc_response = self.trading_engine.session.get_positions(category="linear", settleCoin="USDC")
                self.add_log(f"USDC Positions - retCode: {usdc_response.get('retCode')}")

                if usdc_response.get('retCode') == 0:
                    usdc_positions = usdc_response['result']['list']
                    self.add_log(f"USDC posiciones encontradas: {len(usdc_positions)}")
                    total_positions += len(usdc_positions)

                    for i, pos in enumerate(usdc_positions):
                        symbol = pos.get('symbol', 'Unknown')
                        size = pos.get('size', '0')
                        side = pos.get('side', 'None')
                        unrealized_pnl = pos.get('unrealisedPnl', '0')
                        position_value = pos.get('positionValue', '0')
                        position_idx = pos.get('positionIdx', '0')

                        self.add_log(f"USDC-{i+1}: {symbol} | Size: {size} | Side: {side} | PnL: {unrealized_pnl} | Value: {position_value} | Idx: {position_idx}")
                else:
                    self.add_log(f"Error USDC API: {usdc_response.get('retMsg', 'Error desconocido')}")
            except Exception as usdc_error:
                self.add_log(f"USDC query failed: {usdc_error}")

            self.add_log(f"🔍 Total posiciones encontradas: {total_positions}")

        except AttributeError as e:
            self.add_log(f"❌ Error de atributo: {e}")
            self.add_log("💡 Esto sugiere que la sesión no está inicializada correctamente")
            QMessageBox.critical(self, "Error", f"Error de sesión: {e}")
        except Exception as e:
            self.add_log(f"❌ Error en debug: {e}")
            QMessageBox.critical(self, "Error", f"Error en debug: {e}")

    def reinitialize_trading_engine(self):
        """Reinitialize trading engine with new credentials"""
        try:
            if not MODULES_AVAILABLE:
                return

            # Stop any existing trading engine
            if hasattr(self, 'trading_engine') and self.trading_engine:
                if hasattr(self.trading_engine, 'stop_trading'):
                    self.trading_engine.stop_trading()

            # Create new trading engine with updated credentials
            self.trading_engine = TradingEngine(
                self.config_manager.get_api_key(),
                self.config_manager.get_api_secret(),
                False  # Always use mainnet
            )

            # Initialize session
            if self.trading_engine.initialize_session():
                self.add_log("🔄 Motor de trading reinicializado con nuevas credenciales")
            else:
                self.add_log("⚠️ Error al reinicializar motor de trading")

        except Exception as e:
            self.add_log(f"❌ Error reinicializando motor de trading: {e}")

    def setup_styles(self):
        """Setup application styles with responsive design"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                background-color: white;
                border-radius: 8px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #ecf0f1;
                color: #2c3e50;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
            }
            QTabBar::tab:hover {
                background-color: #d5dbdb;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #bdc3c7;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #95a5a6;
            }
        """)

    def load_saved_settings(self):
        """Load saved settings"""
        if not self.config_manager:
            return

        try:
            # Check if widgets exist before trying to use them
            if not hasattr(self, 'api_key_input') or not hasattr(self, 'api_status_label'):
                print("Widgets not ready for loading settings")
                return

            api_key = self.config_manager.get_api_key()
            api_secret = self.config_manager.get_api_secret()

            self.api_key_input.setText(api_key)
            self.api_secret_input.setText(api_secret)

            # Update status based on whether credentials exist
            if api_key and api_secret:
                self.api_status_label.setText("🟡 Credenciales cargadas desde almacenamiento")
                self.api_status_label.setStyleSheet("""
                    QLabel {
                        color: #f39c12;
                        font-size: 12px;
                        font-weight: bold;
                        margin-top: 10px;
                        padding: 8px 12px;
                        background-color: #fef9e7;
                        border-radius: 4px;
                    }
                """)
                self.add_log("🔑 Credenciales de API guardadas cargadas")
            else:
                self.api_status_label.setText("⚪ Sin credenciales guardadas")

        except Exception as e:
            print(f"Could not load saved settings: {e}")
            # Only try to update status if the widget exists
            if hasattr(self, 'api_status_label'):
                try:
                    self.api_status_label.setText("⚠️ Error cargando credenciales")
                    self.api_status_label.setStyleSheet("""
                        QLabel {
                            color: #e67e22;
                            font-size: 12px;
                            font-weight: bold;
                            margin-top: 10px;
                            padding: 8px 12px;
                            background-color: #fdf2e9;
                            border-radius: 4px;
                        }
                    """)
                except:
                    pass

    def toggle_password(self, line_edit):
        """Toggle password visibility"""
        if line_edit.echoMode() == QLineEdit.Password:
            line_edit.setEchoMode(QLineEdit.Normal)
        else:
            line_edit.setEchoMode(QLineEdit.Password)

    def save_credentials(self):
        """Save API credentials"""
        if not MODULES_AVAILABLE:
            QMessageBox.critical(self, "Error", "Módulos de trading no disponibles")
            return

        api_key = self.api_key_input.text().strip()
        api_secret = self.api_secret_input.text().strip()

        if not api_key or not api_secret:
            QMessageBox.critical(self, "Error", "Por favor ingresa tanto la Clave API como el Secreto API")
            return

        # Confirm save
        reply = QMessageBox.question(
            self,
            "Guardar Credenciales",
            "¿Estás seguro de que quieres guardar estas credenciales de API?\n\n"
            f"Clave API: {api_key[:8]}...{api_key[-8:] if len(api_key) > 16 else api_key}\n\n"
            "Las credenciales serán encriptadas y almacenadas de forma segura.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self.config_manager.set_api_credentials(api_key, api_secret, False)  # Always use mainnet

            # Update status
            self.api_status_label.setText("🟢 Credenciales guardadas exitosamente")
            self.api_status_label.setStyleSheet("""
                QLabel {
                    color: #27ae60;
                    font-size: 12px;
                    font-weight: bold;
                    margin-top: 10px;
                    padding: 8px 12px;
                    background-color: #d5f4e6;
                    border-radius: 4px;
                }
            """)

            QMessageBox.information(self, "Éxito",
                "✅ ¡Credenciales de API guardadas exitosamente!\n\n"
                "Tus credenciales están encriptadas y almacenadas de forma segura.\n"
                "Ahora puedes probar la conexión.")

            self.add_log("🔐 Credenciales de API guardadas y encriptadas de forma segura")

            # Enable test button if both fields are filled
            self.test_btn.setEnabled(True)

            # Reinitialize trading engine with new credentials
            self.reinitialize_trading_engine()

        except Exception as e:
            self.api_status_label.setText("🔴 Error al guardar credenciales")
            self.api_status_label.setStyleSheet("""
                QLabel {
                    color: #e74c3c;
                    font-size: 12px;
                    font-weight: bold;
                    margin-top: 10px;
                    padding: 8px 12px;
                    background-color: #fadbd8;
                    border-radius: 4px;
                }
            """)
            QMessageBox.critical(self, "Error", f"Error al guardar credenciales: {e}")
            self.add_log(f"❌ Error guardando credenciales: {e}")

    def clear_credentials(self):
        """Clear API credentials"""
        if not MODULES_AVAILABLE:
            QMessageBox.critical(self, "Error", "Módulos de trading no disponibles")
            return

        reply = QMessageBox.question(
            self,
            "Limpiar Credenciales",
            "¿Estás seguro de que quieres limpiar todas las credenciales de API guardadas?\n\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self.config_manager.clear_credentials()

            # Clear input fields
            self.api_key_input.clear()
            self.api_secret_input.clear()

            # Update status
            self.api_status_label.setText("⚪ Sin credenciales guardadas")
            self.api_status_label.setStyleSheet("""
                QLabel {
                    color: #7f8c8d;
                    font-size: 12px;
                    font-weight: bold;
                    margin-top: 10px;
                    padding: 8px 12px;
                    background-color: #ecf0f1;
                    border-radius: 4px;
                }
            """)

            QMessageBox.information(self, "Éxito", "✅ ¡Credenciales limpiadas exitosamente!")
            self.add_log("🗑️ Credenciales de API limpiadas")

            # Clear trading engine when credentials are cleared
            if hasattr(self, 'trading_engine') and self.trading_engine:
                if hasattr(self.trading_engine, 'stop_trading'):
                    self.trading_engine.stop_trading()
                self.trading_engine = None
                self.add_log("🔄 Motor de trading desactivado")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear credentials: {e}")
            self.add_log(f"❌ Error clearing credentials: {e}")

    def test_connection(self):
        """Test API connection"""
        if not MODULES_AVAILABLE:
            QMessageBox.critical(self, "Error", "Revisa tu configuración de API")
            return

        api_key = self.api_key_input.text().strip()
        api_secret = self.api_secret_input.text().strip()

        if not api_key or not api_secret:
            QMessageBox.critical(self, "Error", "Revisa tu configuración de API")
            return

        self.add_log("🔍 Testing connection to Bybit...")
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Testing...")

        # Clean up previous connection thread if exists
        if self.connection_thread and self.connection_thread.isRunning():
            self.connection_thread.quit()
            self.connection_thread.wait(1000)

        # Create worker and thread
        self.connection_worker = ConnectionTestWorker(api_key, api_secret)
        self.connection_thread = QThread()

        # Track thread
        self.active_threads.append(self.connection_thread)

        self.connection_worker.moveToThread(self.connection_thread)
        self.connection_thread.started.connect(self.connection_worker.run)
        self.connection_worker.finished.connect(self.on_connection_test_finished)
        self.connection_worker.finished.connect(self.connection_thread.quit)
        self.connection_worker.finished.connect(self.connection_worker.deleteLater)
        self.connection_thread.finished.connect(self.connection_thread.deleteLater)
        self.connection_thread.finished.connect(lambda: self.active_threads.remove(self.connection_thread) if self.connection_thread in self.active_threads else None)

        self.connection_thread.start()

    def on_connection_test_finished(self, success: bool, message: str):
        """Handle connection test result"""
        self.test_btn.setEnabled(True)
        self.test_btn.setText("🔍 Test Connection")

        if success:
            QMessageBox.information(self, "Success", f"✅ {message}")
            self.add_log("✅ Connection test passed")
        else:
            QMessageBox.critical(self, "Error", f"❌ {message}")
            self.add_log(f"❌ {message}")

        # Update connection status
        self.update_connection_status()

    def start_trading(self):
        """Start trading"""
        if not MODULES_AVAILABLE:
            QMessageBox.critical(self, "Error", "Trading modules not available")
            return

        if not self.config_manager or not self.config_manager.has_valid_credentials():
            QMessageBox.critical(self, "Error", "Please configure and test API credentials first")
            return

        symbol = self.symbol_input.text().strip().upper()
        if not symbol:
            QMessageBox.critical(self, "Error", "Please enter a trading symbol")
            return

        sl_enabled = self.sl_checkbox.isChecked()
        tp_enabled = self.tp_checkbox.isChecked()

        if not sl_enabled and not tp_enabled:
            QMessageBox.critical(self, "Error", "Please enable at least one strategy")
            return

        try:
            sl_amount = float(self.sl_amount_input.text()) if sl_enabled else 0
            tp_percentage = float(self.tp_percentage_input.text()) if tp_enabled else 0
        except ValueError:
            QMessageBox.critical(self, "Error", "Please enter valid numeric values")
            return

        self.add_log(f"🚀 Starting trading for {symbol}USDT...")

        # Initialize trading engine for positions monitoring
        if not self.trading_engine:
            try:
                self.trading_engine = TradingEngine(
                    self.config_manager.get_api_key(),
                    self.config_manager.get_api_secret(),
                    False  # Always use mainnet
                )
                # Initialize session for positions monitoring
                self.trading_engine.initialize_session()
            except Exception as e:
                self.add_log(f"⚠️ No se pudo inicializar el motor de posiciones: {e}")

        # Clean up previous trading thread if exists
        if self.trading_thread and self.trading_thread.isRunning():
            self.trading_thread.quit()
            self.trading_thread.wait(2000)

        # Create trading worker
        self.trading_worker = TradingWorker(
            self.config_manager, symbol, sl_enabled, sl_amount, tp_enabled, tp_percentage
        )
        self.trading_thread = QThread()

        # Track thread
        self.active_threads.append(self.trading_thread)

        self.trading_worker.moveToThread(self.trading_thread)
        self.trading_thread.started.connect(self.trading_worker.start_trading)
        self.trading_worker.finished.connect(self.on_trading_finished)
        self.trading_worker.log_message.connect(self.add_log)
        self.trading_thread.finished.connect(lambda: self.active_threads.remove(self.trading_thread) if self.trading_thread in self.active_threads else None)

        self.trading_thread.start()

        # Update UI and trading state
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.is_trading_active = True
        self.status_label.setText("🟢 Trading Active")
        self.statusBar().showMessage("Trading Active")

        # Update status indicators
        self.update_automation_status()

    def stop_trading(self):
        """Stop trading"""
        if self.trading_worker:
            self.trading_worker.stop_trading()

        self.on_trading_stopped()

    def on_trading_finished(self, success: bool, message: str):
        """Handle trading finished"""
        if success:
            self.is_trading_active = True
            self.update_automation_status()
            self.update_order_indicators()
            self.add_log("✅ Trading started successfully")
        else:
            QMessageBox.critical(self, "Error", f"Failed to start trading: {message}")
            self.on_trading_stopped()

    def on_trading_stopped(self):
        """Handle trading stopped"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.is_trading_active = False
        self.update_automation_status()
        self.update_order_indicators()
        self.status_label.setText("⏸️ Stopped")
        self.statusBar().showMessage("Stopped")
        self.add_log("⏹️ Trading stopped")

        # Update status indicators
        self.update_automation_status()

    def add_log(self, message: str):
        """Add message to log with time sync warnings"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"

        # Check for time sync warnings and show popup
        if "desincronizado" in message.lower() or "sincronizar reloj" in message.lower():
            QMessageBox.warning(
                self,
                "⚠️ Advertencia de Sincronización",
                f"Se detectó un problema de sincronización de tiempo:\n\n{message}\n\n"
                "Para solucionarlo:\n"
                "• Windows: Configuración > Hora e idioma > Sincronizar\n"
                "• macOS: Preferencias > Fecha y hora > Automático\n"
                "• Linux: sudo ntpdate -s time.nist.gov"
            )

        self.log_display.append(formatted_message)

    def update_logs(self):
        """Update logs from trading worker"""
        if self.trading_worker and hasattr(self.trading_worker, 'trading_engine'):
            if self.trading_worker.trading_engine and self.trading_worker.trading_engine.log_queue:
                try:
                    while True:
                        try:
                            message = self.trading_worker.trading_engine.log_queue.get_nowait()
                            self.add_log(message)
                        except queue.Empty:
                            break
                except Exception as e:
                    print(f"Log update error: {e}")

    def clear_log(self):
        """Clear log display"""
        self.log_display.clear()
        self.add_log("🗑️ Log cleared")

    def create_about_tab(self):
        """Create comprehensive About tab with comparison analysis"""
        about_widget = QWidget()
        about_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
            }
        """)
        self.tab_widget.addTab(about_widget, "📋 Acerca de")

        # Optimized layout with minimal margins
        main_layout = QVBoxLayout(about_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Create scrollable area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #ffffff;
            }
            QScrollBar:vertical {
                background-color: #ffffff;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #2c3e50;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #1a202c;
            }
        """)

        # Content widget with optimized spacing and white background
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
            }
        """)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(10, 10, 10, 10)

        # Header Section
        self.create_about_header(content_layout)

        # Added Features Section
        self.create_features_section(content_layout)

        # Support Section
        self.create_support_section(content_layout)

        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def create_about_header(self, parent_layout):
        """Create header section with attribution"""
        # Main title
        title = QLabel("🚀 SL y TP Automático Unificado para Bybit")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #1a202c;
                margin-bottom: 10px;
                text-align: center;
                background-color: #ffffff;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        parent_layout.addWidget(title)

        # Credit text - modern, direct layout without boxes
        credit_text = QLabel("""
        <b>🎯 Desarrollo y Unificación:</b><br>
        Esta interfaz gráfica unificada fue desarrollada por <b>Juan David Garcia</b><br>
        (<a href="https://github.com/codavidgarcia" style="color: #1a5490; text-decoration: underline;">GitHub</a> |
        <a href="https://t.me/codavidgarcia" style="color: #1a5490; text-decoration: underline;">Telegram</a>)
        para proporcionar acceso fácil y moderno a las herramientas de trading<br>
        originalmente desarrolladas por <b>Andrés Perea (El gafas trading)</b>.

        <br><br><b>📜 Scripts Originales:</b><br>
        • <a href="https://github.com/ElGafasTrading/StopLossBybit" style="color: #1a5490; text-decoration: underline;">StopLossBybit</a> - Automatización de Stop Loss<br>
        • <a href="https://github.com/ElGafasTrading/takeProfitBybit" style="color: #1a5490; text-decoration: underline;">takeProfitBybit</a> - Automatización de Take Profit
        """)
        credit_text.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #1a202c;
                line-height: 1.5;
                background-color: #ffffff;
                padding: 15px;
                border-left: 3px solid #1a5490;
                margin: 10px 0px;
            }
        """)
        credit_text.setWordWrap(True)
        credit_text.setOpenExternalLinks(True)
        parent_layout.addWidget(credit_text)

    def create_features_section(self, parent_layout):
        """Create modern, clean features section without nested boxes"""
        # Section title
        features_title = QLabel("✨ Características Agregadas")
        features_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #1a202c;
                margin: 20px 0px 15px 0px;
                background-color: #ffffff;
            }
        """)
        parent_layout.addWidget(features_title)

        # Direct content without nested frames
        features_content = QLabel("""
        • Stop Loss y Take Profit en una sola aplicación<br>
        • Actualización automática de SL / TP en vivo y durante un trade abierto
        • Interfaz gráfica pensada para satisfacer a usuarios novatos y avanzados<br>
        • Soporte para modo hedge (cobertura) de Bybit<br>
        • Detección automática y auto-configuración de funcionamiento en caso de modo cobertura<br>
        • Configuración visual de credenciales API mediante interfaz<br>
        • Sistema de pestañas para organizar funciones<br>
        • Botones de prueba de conexión con retroalimentación visual para confirmación de Estado de Conexión<br><br>
        • Selección automática de ticker cuando hay una sola posición abierta por el usuario<br>
        • Botón "seleccionar" cuando hay múltiples posiciones abiertas por el usuario<br>
        • Indicadores de estado del SL/TP automáticos con círculos de color<br>
        • Actualización automática al cambiar de pestaña<br><br>
        • Tabla de posiciones abiertas con datos en tiempo real actualizados cada 5 segundos<br>
        • Tarjetas de resumen con Total de Posiciones, PnL y Valor en USDT<br>
        • Logs con timestamps y mensajes de estado en la vista de Monitor en Vivo<br>
        • Botón de actualización manual y modo automático para las posiciones (se puede desactivar para ahorrar requests)<br><br>
        • Manejo de errores avanzado con diálogos informativos<br>
        • Guardado automático de configuración para facilidad del usuario
        """)
        features_content.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #1a202c;
                line-height: 1.4;
                background-color: #ffffff;
                padding: 15px;
                border-left: 3px solid #27ae60;
                margin: 5px 0px;
            }
        """)
        features_content.setWordWrap(True)
        parent_layout.addWidget(features_content)



    def create_support_section(self, parent_layout):
        """Create support and donation section"""
        # Section title - modern spacing
        support_title = QLabel("💝 Apoyo y Reconocimiento")
        support_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #1a202c;
                margin: 20px 0px 15px 0px;
                background-color: #ffffff;
            }
        """)
        parent_layout.addWidget(support_title)

        # Support text - direct, no frame
        support_text = QLabel("""
        Si esta aplicación te ha sido útil y ha mejorado tu experiencia de trading,
        considera apoyar el desarrollo continuo y mostrar tu aprecio (aunque sea con un Star en Github):
        """)
        support_text.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #1a202c;
                margin-bottom: 15px;
                text-align: center;
                background-color: #ffffff;
                padding: 10px;
            }
        """)
        support_text.setAlignment(Qt.AlignCenter)
        support_text.setWordWrap(True)
        parent_layout.addWidget(support_text)

        # Buttons layout - direct to parent
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        buttons_layout.setContentsMargins(0, 10, 0, 0)

        # PayPal donation button
        paypal_btn = QPushButton("💳 Donar via PayPal")
        paypal_btn.setStyleSheet("""
            QPushButton {
                background-color: #0070ba;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                min-width: 160px;
            }
            QPushButton:hover {
                background-color: #005ea6;
            }
        """)
        paypal_btn.clicked.connect(lambda: self.open_donation_link("http://paypal.me/cojuangarcia"))
        buttons_layout.addWidget(paypal_btn)

        # Crypto donation button
        crypto_btn = QPushButton("₿ Donar Crypto")
        crypto_btn.setStyleSheet("""
            QPushButton {
                background-color: #f7931a;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                min-width: 160px;
            }
            QPushButton:hover {
                background-color: #e8851a;
            }
        """)
        crypto_btn.clicked.connect(lambda: self.show_donation_info("Crypto"))
        buttons_layout.addWidget(crypto_btn)

        # GitHub star button
        github_btn = QPushButton("⭐ Star en GitHub")
        github_btn.setStyleSheet("""
            QPushButton {
                background-color: #24292e;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                min-width: 160px;
            }
            QPushButton:hover {
                background-color: #1b1f23;
            }
        """)
        github_btn.clicked.connect(lambda: self.open_donation_link("https://github.com/codavidgarcia"))
        buttons_layout.addWidget(github_btn)

        parent_layout.addLayout(buttons_layout)

    def open_donation_link(self, url):
        """Open donation link in default browser"""
        import webbrowser
        webbrowser.open(url)

    def show_donation_info(self, donation_type):
        """Show donation information dialog"""
        if donation_type == "PayPal":
            QMessageBox.information(self, "PayPal Donation",
                "💳 Donación via PayPal:\n\n"
                "http://paypal.me/cojuangarcia\n\n"
                "¡Gracias por tu apoyo al proyecto!")
        elif donation_type == "Crypto":
            QMessageBox.information(self, "Crypto Donation",
                "₿ Donación Crypto:\n\n"
                "Moneda: USDT\n"
                "Red: Tron (TRC20)\n"
                "Dirección: TApSFrenRkfbYtGKFb6478eEZPxtZkfody\n\n"
                "¡Gracias por tu apoyo al proyecto!")
        elif donation_type == "GitHub":
            QMessageBox.information(self, "GitHub Repository",
                "⭐ Dale una estrella en GitHub:\n\n"
                "https://github.com/codavidgarcia\n\n"
                "¡Tu apoyo es muy apreciado!")


def main():
    """Main function"""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Unified Bybit Trading Bot")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Trading Bot")

    # Create and show main window
    window = PySideTradingGUI()
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    print("🚀 Iniciando SL/TP Automático en Bybit...")
    main()
