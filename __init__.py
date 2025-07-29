"""
Jarvis Assistant - A Modular Voice-Controlled AI Assistant

A Python-based voice assistant that can:
- Listen for voice commands
- Parse and execute system functions
- Respond with synthesized speech
- Maintain state and goals
- Be extended with daily feature additions

Author: Built with Claude Code
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Built with Claude Code"

from .main import JarvisAssistant
from .voice_input import VoiceInput
from .command_parser import CommandParser
from .elevenlabs_output import ElevenLabsOutput
from .jarvis_state import JarvisState, jarvis_state
from .config import Config, config

__all__ = [
    "JarvisAssistant",
    "VoiceInput", 
    "CommandParser",
    "ElevenLabsOutput",
    "JarvisState",
    "jarvis_state",
    "Config",
    "config"
]