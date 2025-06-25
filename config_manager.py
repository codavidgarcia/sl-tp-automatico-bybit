import json
import os
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import base64


class ConfigManager:
    """Manages configuration settings and API credentials securely"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = {}
        self.encryption_key = None
        self._generate_or_load_key()
        self.load_config()
    
    def _generate_or_load_key(self):
        """Generate or load encryption key for API credentials"""
        key_file = "key.key"
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                self.encryption_key = f.read()
        else:
            self.encryption_key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(self.encryption_key)
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not data:
            return ""
        fernet = Fernet(self.encryption_key)
        encrypted = fernet.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not encrypted_data:
            return ""
        try:
            fernet = Fernet(self.encryption_key)
            decoded = base64.b64decode(encrypted_data.encode())
            decrypted = fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception:
            return ""
    
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                self.config = {}
        else:
            self.config = self._get_default_config()
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "api_credentials": {
                "api_key": "",
                "api_secret": "",
                "testnet": False
            },
            "trading_settings": {
                "default_symbol": "BTC",
                "default_stop_loss": 10.0,
                "default_take_profit": 2.0,
                "auto_start": False
            },
            "ui_settings": {
                "theme": "light",
                "window_size": "800x600",
                "log_max_lines": 1000
            }
        }
    
    def get_api_key(self) -> str:
        """Get decrypted API key"""
        encrypted_key = self.config.get("api_credentials", {}).get("api_key", "")
        return self._decrypt_data(encrypted_key)
    
    def get_api_secret(self) -> str:
        """Get decrypted API secret"""
        encrypted_secret = self.config.get("api_credentials", {}).get("api_secret", "")
        return self._decrypt_data(encrypted_secret)
    
    def set_api_credentials(self, api_key: str, api_secret: str, testnet: bool = False):
        """Set encrypted API credentials"""
        if "api_credentials" not in self.config:
            self.config["api_credentials"] = {}
        
        self.config["api_credentials"]["api_key"] = self._encrypt_data(api_key)
        self.config["api_credentials"]["api_secret"] = self._encrypt_data(api_secret)
        self.config["api_credentials"]["testnet"] = testnet
        self.save_config()
    
    def get_testnet_mode(self) -> bool:
        """Get testnet mode setting"""
        return self.config.get("api_credentials", {}).get("testnet", False)
    
    def get_trading_setting(self, key: str, default=None):
        """Get trading setting"""
        return self.config.get("trading_settings", {}).get(key, default)
    
    def set_trading_setting(self, key: str, value):
        """Set trading setting"""
        if "trading_settings" not in self.config:
            self.config["trading_settings"] = {}
        self.config["trading_settings"][key] = value
        self.save_config()
    
    def get_ui_setting(self, key: str, default=None):
        """Get UI setting"""
        return self.config.get("ui_settings", {}).get(key, default)
    
    def set_ui_setting(self, key: str, value):
        """Set UI setting"""
        if "ui_settings" not in self.config:
            self.config["ui_settings"] = {}
        self.config["ui_settings"][key] = value
        self.save_config()
    
    def has_valid_credentials(self) -> bool:
        """Check if valid API credentials are configured"""
        api_key = self.get_api_key()
        api_secret = self.get_api_secret()
        return bool(api_key and api_secret)
    
    def clear_credentials(self):
        """Clear API credentials"""
        if "api_credentials" in self.config:
            self.config["api_credentials"]["api_key"] = ""
            self.config["api_credentials"]["api_secret"] = ""
            self.save_config()
    
    def export_settings(self, file_path: str) -> bool:
        """Export non-sensitive settings to file"""
        try:
            export_config = {
                "trading_settings": self.config.get("trading_settings", {}),
                "ui_settings": self.config.get("ui_settings", {})
            }
            with open(file_path, 'w') as f:
                json.dump(export_config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False
    
    def import_settings(self, file_path: str) -> bool:
        """Import non-sensitive settings from file"""
        try:
            with open(file_path, 'r') as f:
                imported_config = json.load(f)
            
            # Only import non-sensitive settings
            if "trading_settings" in imported_config:
                self.config["trading_settings"] = imported_config["trading_settings"]
            if "ui_settings" in imported_config:
                self.config["ui_settings"] = imported_config["ui_settings"]
            
            self.save_config()
            return True
        except Exception as e:
            print(f"Error importing settings: {e}")
            return False
