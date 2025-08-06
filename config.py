"""
Configuration management for Jarvis Assistant.
Handles API keys, settings, and environment variables.
"""

import json
import os
import logging
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv
import stat

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Central configuration class for Jarvis with security features."""
    
    def __init__(self):
        """Initialize configuration with default values and security checks."""
        self.config_file = Path("config.json")
        self._secure_config_file()
        self.load_config()
    
    def load_config(self):
        """Load configuration from file or create default securely."""
        if self.config_file.exists():
            try:
                # Verify file permissions before reading
                file_stat = self.config_file.stat()
                if file_stat.st_mode & 0o077:  # Check if readable by group/others
                    logging.warning(f"Config file {self.config_file} has insecure permissions")
                
                with open(self.config_file, 'r') as f:
                    self.data = json.load(f)
                    
                # Validate loaded configuration
                self._validate_config()
                
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Failed to load config file: {e}")
                self._create_default_config()
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default configuration without sensitive data."""
        self.data = {
            "elevenlabs": {
                "api_key": "",  # Never store API keys in config file
                "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Default voice
                "model_id": "eleven_monolingual_v1"
            },
            "speech_recognition": {
                "engine": "whisper",  # Options: "google", "whisper"
                "language": "en-US",
                "timeout": 1,
                "phrase_timeout": 3
            },
            "general": {
                "wake_word": "jarvis",
                "response_delay": 0.5,
                "max_listening_time": 10
            },
            "security": {
                "rate_limit_enabled": True,
                "max_requests_per_minute": 60,
                "log_security_events": True
            }
        }
        self.save_config()
    
    def _validate_config(self):
        """Validate configuration data for security issues."""
        # Check for API keys accidentally stored in config
        sensitive_keys = ["api_key", "secret", "password", "token"]
        for section_name, section in self.data.items():
            if isinstance(section, dict):
                for key, value in section.items():
                    if any(sensitive in key.lower() for sensitive in sensitive_keys):
                        if value and len(str(value)) > 10:  # Likely a real API key
                            logging.warning(f"Potential API key found in config: {section_name}.{key}")
    
    def _secure_config_file(self):
        """Ensure config file has secure permissions."""
        if self.config_file.exists():
            try:
                # Set secure permissions (readable/writable by owner only)
                self.config_file.chmod(0o600)
            except OSError as e:
                logging.warning(f"Failed to set secure permissions on config file: {e}")
    
    def save_config(self):
        """Save current configuration to file securely."""
        try:
            # Validate before saving
            self._validate_config()
            
            with open(self.config_file, 'w') as f:
                json.dump(self.data, f, indent=4)
            
            # Set secure permissions after writing
            self._secure_config_file()
            
        except (IOError, OSError) as e:
            logging.error(f"Failed to save config file: {e}")
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value with environment variable override."""
        # Check environment variable first (more secure)
        env_key = f"{section.upper()}_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
        
        # Fallback to config file
        return self.data.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Any):
        """Set configuration value and save (warns about sensitive data)."""
        # Warn if trying to store sensitive data
        sensitive_keys = ["api_key", "secret", "password", "token"]
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            logging.warning(f"Attempting to store sensitive data in config: {section}.{key}. Consider using environment variables instead.")
        
        if section not in self.data:
            self.data[section] = {}
        self.data[section][key] = value
        self.save_config()
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Securely get API key from environment variables."""
        env_key = f"{service.upper()}_API_KEY"
        api_key = os.getenv(env_key)
        
        if not api_key:
            logging.warning(f"API key not found for service: {service}. Set environment variable: {env_key}")
            return None
            
        return api_key

# Global config instance
config = Config()