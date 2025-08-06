"""
Jarvis Assistant - Main Entry Point.

A modular voice-controlled AI assistant built in Python that demonstrates
advanced architecture patterns and component integration.

This main orchestrator coordinates all system components:
- Voice input with wake word detection and speech recognition
- Natural language command parsing and execution
- High-quality voice output using ElevenLabs TTS
- Persistent state management with JSON storage
- Multi-mode operation (voice, text, test)
- Graceful error handling and shutdown

Supported execution modes:
- Voice Mode: Full voice control with wake word detection
- Text Mode: Interactive command-line interface
- Test Mode: Comprehensive system diagnostics

Usage:
    python main.py [mode]    # mode: voice, text, test
    python main.py           # Interactive mode selection
"""

import os
import sys
import time
import signal
import threading
from typing import Optional
from pathlib import Path

# Suppress console errors BEFORE any imports
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
os.environ['ALSA_PCM_CARD'] = '0' 
os.environ['ALSA_PCM_DEVICE'] = '0'
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pygame')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='pkg_resources')
warnings.filterwarnings('ignore', message='.*telemetry.*')

# Import Jarvis modules
from voice_input import VoiceInput
from command_parser import CommandParser
from elevenlabs_output import ElevenLabsOutput
from memory.state_manager import jarvis_state
from memory.chroma_manager import chroma_manager
from memory.conversation_manager import conversation_manager
from config import config

class JarvisAssistant:
    """Main Jarvis Assistant class that orchestrates all components."""
    
    def __init__(self):
        """Initialize Jarvis with all necessary components."""
        print("🤖 Initializing Jarvis Assistant...")
        
        # Initialize components
        self.voice_input = None
        self.command_parser = None
        self.voice_output = None
        self.is_running = False
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Initialize all components
        self._initialize_components()
        
        # Update state with current task
        jarvis_state.set_current_task("claude", "Jarvis system initialization complete")
        
        print("✅ Jarvis Assistant initialized successfully!")
        print(f"   - Voice recognition: {'✅ Ready' if self.voice_input else '❌ Failed'}")
        print(f"   - Command parsing: {'✅ Ready' if self.command_parser else '❌ Failed'}")
        print(f"   - Voice output: {'✅ Ready' if self.voice_output else '❌ Failed'}")
        print()
    
    def _initialize_components(self):
        """Initialize all Jarvis components."""
        try:
            # Initialize command parser
            print("📝 Initializing command parser...")
            self.command_parser = CommandParser()
            
            # Initialize voice output
            print("🔊 Initializing voice output...")
            self.voice_output = ElevenLabsOutput()
            
            # Initialize voice input (this might take a moment)
            print("🎤 Initializing voice input...")
            self.voice_input = VoiceInput()
            
            jarvis_state.log_action("jarvis_initialized", "All components loaded successfully", "main")
            
        except Exception as e:
            print(f"❌ Error initializing components: {e}")
            jarvis_state.log_action("initialization_error", str(e), "main")
            raise
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        print(f"\\n🛑 Received signal {signum}. Shutting down gracefully...")
        self.shutdown()
        sys.exit(0)
    
    def _handle_voice_command(self, command_text: str):
        """
        Handle a voice command from the user.
        
        Args:
            command_text: The recognized speech text
        """
        print(f"🎯 Processing command: {command_text}")
        
        # Parse and execute the command
        response = self.command_parser.parse_command(command_text)
        
        if response:
            print(f"💬 Response: {response}")
            
            # Speak the response
            if self.voice_output:
                self.voice_output.speak(response)
            
            # Check if this is a quit command
            if "shutting down" in response.lower():
                print("👋 Goodbye!")
                self.shutdown()
                return
        
        print("🎤 Listening for next command...")
    
    def run_interactive_mode(self):
        """Run Jarvis in interactive text mode (no voice)."""
        print("🖥️  Starting Jarvis in Interactive Text Mode")
        print("   Type commands or 'quit' to exit")
        print("   Type 'help' to see available commands")
        print("-" * 50)
        
        self.is_running = True
        jarvis_state.set_current_task("user", "Interactive text mode")
        
        try:
            while self.is_running:
                try:
                    # Get text input from user
                    command = input("jarvis> ").strip()
                    
                    if not command:
                        continue
                    
                    # Process the command
                    self._handle_voice_command(command)
                    
                except EOFError:
                    # Handle Ctrl+D
                    print("\\n👋 Goodbye!")
                    break
                except KeyboardInterrupt:
                    # Handle Ctrl+C
                    print("\\n👋 Goodbye!")
                    break
                    
        finally:
            self.shutdown()
    
    def run_voice_mode(self):
        """Run Jarvis in voice-controlled mode."""
        if not self.voice_input:
            print("❌ Voice input not available. Starting in text mode instead.")
            self.run_interactive_mode()
            return
        
        print("🎤 Starting Jarvis in Voice Mode")
        print("   Speak your commands directly - no wake word needed")
        print("   Say 'goodbye' to stop")
        print("-" * 50)
        
        self.is_running = True
        jarvis_state.set_current_task("user", "Voice control mode")
        
        # Speak personalized greeting based on memory
        if self.voice_output:
            greeting = conversation_manager.get_greeting()
            print(f"🤖 Jarvis: {greeting}")
            self.voice_output.speak(greeting)
        
        try:
            # Start voice input in conversation mode (no wake word needed)
            self.voice_input.start_conversation_async(self._handle_voice_command)
            
            # Keep main thread alive
            while self.is_running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\\n👋 Shutting down...")
        finally:
            self.shutdown()
    
    def run_test_mode(self):
        """Run system tests to verify all components work."""
        print("🧪 Running Jarvis System Tests")
        print("-" * 40)
        
        all_tests_passed = True
        
        # Test 1: Command Parser
        print("1. Testing Command Parser...")
        test_response = self.command_parser.parse_command("what time is it")
        if "time is" in test_response:
            print("   ✅ Command parser working")
        else:
            print("   ❌ Command parser failed")
            all_tests_passed = False
        
        # Test 2: Voice Output (if API key available)
        print("2. Testing Voice Output...")
        if self.voice_output and self.voice_output.api_key:
            if self.voice_output.test_speech("Testing Jarvis voice output"):
                print("   ✅ Voice output working")
            else:
                print("   ❌ Voice output failed")
                all_tests_passed = False
        else:
            print("   ⚠️  Voice output skipped (no API key)")
        
        # Test 3: Voice Input
        print("3. Testing Voice Input...")
        if self.voice_input:
            if self.voice_input.test_microphone():
                print("   ✅ Voice input working")
            else:
                print("   ❌ Voice input failed")
                all_tests_passed = False
        else:
            print("   ❌ Voice input not initialized")
            all_tests_passed = False
        
        # Test 4: State Management
        print("4. Testing State Management...")
        try:
            goals = jarvis_state.get_goals()
            jarvis_state.add_todo("Test todo item", "system", "low")
            todos = jarvis_state.get_todos()
            if goals and todos:
                print("   ✅ State management working")
            else:
                print("   ❌ State management failed")
                all_tests_passed = False
        except Exception as e:
            print(f"   ❌ State management error: {e}")
            all_tests_passed = False
        
        print("-" * 40)
        if all_tests_passed:
            print("🎉 All tests passed! Jarvis is ready to go.")
        else:
            print("⚠️  Some tests failed. Check the issues above.")
        
        return all_tests_passed
    
    def shutdown(self):
        """Gracefully shutdown Jarvis."""
        if not self.is_running:
            return
        
        print("🛑 Shutting down Jarvis...")
        self.is_running = False
        
        # Stop voice input
        if self.voice_input:
            self.voice_input.stop_listening()
        
        # Stop any audio playback
        if self.voice_output:
            self.voice_output.stop_playback()
        
        # Log shutdown
        jarvis_state.log_action("jarvis_shutdown", "System shutdown completed", "main")
        jarvis_state.set_current_task("claude", None)
        
        print("✅ Jarvis shutdown complete")

def main():
    """Main entry point for Jarvis Assistant."""
    print("=" * 60)
    print("🤖 JARVIS - Voice-Controlled AI Assistant")
    print("   A modular Python-based assistant")
    print("=" * 60)
    
    try:
        # Initialize Jarvis
        jarvis = JarvisAssistant()
        
        # Check command line arguments
        if len(sys.argv) > 1:
            mode = sys.argv[1].lower()
            
            if mode == "test":
                jarvis.run_test_mode()
            elif mode == "text":
                jarvis.run_interactive_mode()
            elif mode == "voice":
                jarvis.run_voice_mode()
            else:
                print(f"Unknown mode: {mode}")
                print("Available modes: test, text, voice")
                sys.exit(1)
        else:
            # Default behavior: try voice mode, fall back to text
            print("🎯 Choose mode:")
            print("   [1] Voice Mode (recommended)")
            print("   [2] Text Mode (backup)")
            print("   [3] Test Mode (diagnostics)")
            print()
            
            try:
                choice = input("Enter choice (1-3) or press Enter for voice mode: ").strip()
                
                if choice == "2":
                    jarvis.run_interactive_mode()
                elif choice == "3":
                    jarvis.run_test_mode()
                else:
                    jarvis.run_voice_mode()
                    
            except (EOFError, KeyboardInterrupt):
                print("\\n👋 Goodbye!")
                
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        jarvis_state.log_action("fatal_error", str(e), "main")
        sys.exit(1)

if __name__ == "__main__":
    main()