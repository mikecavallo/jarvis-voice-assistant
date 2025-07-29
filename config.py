"""
Configuration management for Jarvis Assistant.
Handles API keys, settings, and environment variables.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Central configuration class for Jarvis."""
    
    def __init__(self):
        """Initialize configuration with default values."""
        self.config_file = Path("config.json")
        self.load_config()
    
    def load_config(self):
        """Load configuration from file or create default."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.data = json.load(f)
        else:
            # Create default configuration
            self.data = {
                "elevenlabs": {
                    "api_key": os.getenv("ELEVENLABS_API_KEY", ""),
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
                }
            }
            self.save_config()
    
    def save_config(self):
        """Save current configuration to file."""
        with open(self.config_file, 'w') as f:
            json.dump(self.data, f, indent=4)
    
    def get(self, section, key, default=None):
        """Get configuration value with fallback to default."""
        return self.data.get(section, {}).get(key, default)
    
    def set(self, section, key, value):
        """Set configuration value and save."""
        if section not in self.data:
            self.data[section] = {}
        self.data[section][key] = value
        self.save_config()

# Global config instance
config = Config()