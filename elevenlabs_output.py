"""
ElevenLabs Voice Output Module for Jarvis Assistant.

This module provides text-to-speech capabilities using the ElevenLabs API.
It handles:
- Text-to-speech conversion via ElevenLabs API
- Audio playback using pygame mixer
- Voice selection and configuration
- Error handling and API validation
- Audio file saving capabilities

The module is designed to work robustly with network issues and provides
fallback behavior when API keys are missing or connections fail.
"""

import os
import tempfile
import time
from typing import Optional
import pygame
import requests
from pathlib import Path
from config import config
from memory.state_manager import jarvis_state

class ElevenLabsOutput:
    """
    Manages text-to-speech synthesis and audio playback for Jarvis Assistant.
    
    This class provides a complete TTS solution using ElevenLabs API with:
    - High-quality voice synthesis
    - Configurable voice selection
    - Audio playback with pygame
    - API connection validation
    - Error recovery and logging
    
    Attributes:
        api_key (str): ElevenLabs API key from configuration
        voice_id (str): Selected voice ID for synthesis
        model_id (str): ElevenLabs model to use for generation
        base_url (str): ElevenLabs API base URL
    """
    
    def __init__(self):
        """
        Initialize ElevenLabs output with API configuration and audio system.
        
        Sets up the TTS engine by:
        1. Loading configuration from config.json
        2. Initializing pygame mixer for audio playback
        3. Validating API key and testing connection
        4. Logging initialization status
        """
        # Load configuration settings
        self.api_key = config.get("elevenlabs", "api_key")
        self.voice_id = config.get("elevenlabs", "voice_id", "21m00Tcm4TlvDq8ikWAM")
        self.model_id = config.get("elevenlabs", "model_id", "eleven_monolingual_v1")
        self.base_url = "https://api.elevenlabs.io/v1"
        
        # Initialize pygame mixer with optimized settings for speech
        self._initialize_audio_system()
        
        # Validate API key and test connection
        self._validate_configuration()
    
    def _initialize_audio_system(self):
        """
        Initialize pygame mixer with optimal settings for speech playback.
        
        Uses configuration optimized for voice synthesis:
        - 22050 Hz sample rate (adequate for speech)
        - 16-bit signed audio
        - Stereo output
        - Small buffer for low latency
        """
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        except Exception as e:
            print(f"Warning: Could not initialize audio system: {e}")
            jarvis_state.log_action("audio_init_failed", str(e), "elevenlabs_output")
    
    def _validate_configuration(self):
        """
        Validate API configuration and test connection.
        
        Checks for API key presence and tests the connection to ElevenLabs.
        Logs appropriate status messages for debugging.
        """
        if not self.api_key:
            print("Warning: ElevenLabs API key not set - responses will be text only.")
            print("Set ELEVENLABS_API_KEY in your .env file to enable voice output.")
            jarvis_state.log_action("elevenlabs_no_key", "API key missing", "elevenlabs_output")
        else:
            jarvis_state.log_action("elevenlabs_initialized", f"Using voice ID: {self.voice_id}", "elevenlabs_output")
            self._test_api_connection()
    
    def _test_api_connection(self) -> bool:
        """
        Test connection to ElevenLabs API by fetching available voices.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            headers = self._get_api_headers("application/json")
            response = requests.get(f"{self.base_url}/voices", headers=headers, timeout=10)
            
            if response.status_code == 200:
                jarvis_state.log_action("elevenlabs_connected", "API connection successful", "elevenlabs_output")
                return True
            else:
                jarvis_state.log_action("elevenlabs_connection_failed", f"Status: {response.status_code}", "elevenlabs_output")
                print(f"ElevenLabs API connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            jarvis_state.log_action("elevenlabs_connection_error", str(e), "elevenlabs_output")
            print(f"ElevenLabs API connection error: {e}")
            return False
    
    def _get_api_headers(self, content_type: str = "application/json") -> dict:
        """
        Generate standard API headers for ElevenLabs requests.
        
        Args:
            content_type: Content-Type header value
            
        Returns:
            dict: Headers dictionary with API key and content type
        """
        return {
            "Accept": content_type,
            "xi-api-key": self.api_key
        }
    
    def speak(self, text: str, save_audio: bool = False) -> bool:
        """
        Convert text to speech and play it through the audio system.
        
        This is the main entry point for text-to-speech functionality.
        It handles the complete pipeline: text validation, API call,
        audio generation, and playback.
        
        Args:
            text: Text to convert to speech (must not be empty)
            save_audio: If True, saves audio file to audio_output directory
            
        Returns:
            bool: True if synthesis and playback successful, False otherwise
        """
        # Validate input text
        if not text or not text.strip():
            return False
        
        # Check API key availability
        if not self.api_key:
            print(f"Text-to-speech disabled (no API key): {text}")
            return False
        
        # Log the TTS request
        jarvis_state.log_action("tts_request", f"Speaking: {text[:50]}...", "elevenlabs_output")
        
        try:
            # Generate speech audio from ElevenLabs API
            audio_data = self._generate_speech(text)
            if not audio_data:
                return False
            
            # Play the generated audio
            success = self._play_audio(audio_data, text if save_audio else None)
            
            if success:
                jarvis_state.log_action("tts_success", "Speech played successfully", "elevenlabs_output")
            
            return success
            
        except Exception as e:
            jarvis_state.log_action("tts_error", str(e), "elevenlabs_output")
            print(f"Error in text-to-speech: {e}")
            return False
    
    def _generate_speech(self, text: str) -> Optional[bytes]:
        """
        Generate speech audio from text using ElevenLabs API.
        
        Makes a POST request to the ElevenLabs text-to-speech endpoint
        with optimized voice settings for natural-sounding speech.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            bytes: MP3 audio data, or None if generation failed
        """
        try:
            url = f"{self.base_url}/text-to-speech/{self.voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            # Voice settings optimized for natural speech
            payload = {
                "text": text,
                "model_id": self.model_id,
                "voice_settings": {
                    "stability": 0.5,           # Balanced stability
                    "similarity_boost": 0.5,    # Natural voice similarity
                    "style": 0.0,               # Neutral style
                    "use_speaker_boost": True   # Enhanced clarity
                }
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.content
            else:
                # Handle quota exceeded more gracefully
                if response.status_code == 401 and "quota_exceeded" in response.text:
                    print("⚠️  ElevenLabs voice quota exceeded - continuing without voice output")
                else:
                    print(f"ElevenLabs API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print("ElevenLabs API request timed out")
            return None
        except Exception as e:
            print(f"Error generating speech: {e}")
            return None
    
    def _play_audio(self, audio_data: bytes, save_filename: Optional[str] = None) -> bool:
        """
        Play audio data using pygame mixer and optionally save to file.
        
        Creates a temporary file for pygame to load, plays the audio,
        waits for completion, and handles cleanup. Optionally saves
        the audio to the audio_output directory.
        
        Args:
            audio_data: MP3 audio bytes from ElevenLabs API
            save_filename: If provided, saves audio with this filename
            
        Returns:
            bool: True if playback successful, False otherwise
        """
        temp_file_path = None
        
        try:
            # Create temporary file for pygame to load
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Load and play the audio file
            pygame.mixer.music.load(temp_file_path)
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            # Save audio file if requested
            if save_filename:
                self._save_audio_file(audio_data, save_filename)
            
            return True
                
        except Exception as e:
            print(f"Error playing audio: {e}")
            return False
            
        finally:
            # Always clean up temporary file
            if temp_file_path:
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass  # File cleanup failed, but not critical
    
    def _save_audio_file(self, audio_data: bytes, filename: str):
        """
        Save audio data to the audio_output directory.
        
        Args:
            audio_data: Audio bytes to save
            filename: Base filename (without extension)
        """
        try:
            save_path = Path("audio_output") / f"{filename}.mp3"
            save_path.parent.mkdir(exist_ok=True)
            
            with open(save_path, 'wb') as f:
                f.write(audio_data)
            
            print(f"Audio saved to: {save_path}")
            jarvis_state.log_action("audio_saved", str(save_path), "elevenlabs_output")
            
        except Exception as e:
            print(f"Warning: Could not save audio file: {e}")
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Change the voice used for speech synthesis.
        
        Validates the new voice ID by checking if it exists in the
        ElevenLabs voice library, then updates the configuration.
        
        Args:
            voice_id: ElevenLabs voice ID to switch to
            
        Returns:
            bool: True if voice change successful, False if invalid voice ID
        """
        if not self.api_key:
            print("Cannot change voice: No API key configured")
            return False
            
        try:
            # Validate voice exists by fetching voice information
            headers = self._get_api_headers("application/json")
            response = requests.get(f"{self.base_url}/voices/{voice_id}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.voice_id = voice_id
                config.set("elevenlabs", "voice_id", voice_id)
                jarvis_state.log_action("voice_changed", f"Voice changed to: {voice_id}", "elevenlabs_output")
                print(f"Voice successfully changed to: {voice_id}")
                return True
            else:
                print(f"Invalid voice ID: {voice_id} (Status: {response.status_code})")
                return False
                
        except Exception as e:
            print(f"Error setting voice: {e}")
            return False
    
    def list_available_voices(self) -> Optional[list]:
        """
        Get list of available voices from ElevenLabs API.
        
        Fetches the complete voice library with metadata including
        voice names, descriptions, and IDs for voice selection.
        
        Returns:
            list: List of voice dictionaries with voice information,
                 or None if request failed
        """
        if not self.api_key:
            print("Cannot list voices: No API key configured")
            return None
            
        try:
            headers = self._get_api_headers("application/json")
            response = requests.get(f"{self.base_url}/voices", headers=headers, timeout=10)
            
            if response.status_code == 200:
                voices_data = response.json()
                return voices_data.get("voices", [])
            else:
                print(f"Error fetching voices: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error listing voices: {e}")
            return None
    
    def test_speech(self, test_text: str = "Hello! This is Jarvis testing the speech output.") -> bool:
        """
        Test the complete speech synthesis and playback system.
        
        Performs a full end-to-end test of TTS functionality including
        API connection, speech generation, and audio playback.
        
        Args:
            test_text: Text to use for testing (uses default test message if not provided)
            
        Returns:
            bool: True if all components working correctly, False otherwise
        """
        print(f"Testing speech synthesis with: '{test_text}'")
        return self.speak(test_text)
    
    def stop_playback(self):
        """
        Stop any currently playing audio immediately.
        
        Interrupts ongoing speech synthesis playback, useful for
        stopping long responses or handling user interruptions.
        """
        try:
            pygame.mixer.music.stop()
            jarvis_state.log_action("playback_stopped", "Audio playback stopped", "elevenlabs_output")
        except Exception as e:
            print(f"Error stopping playback: {e}")
    
    def get_current_voice_info(self) -> dict:
        """
        Get information about the currently selected voice.
        
        Returns:
            dict: Current voice configuration including voice_id and model_id
        """
        return {
            "voice_id": self.voice_id,
            "model_id": self.model_id,
            "api_connected": bool(self.api_key)
        }

# Module test function for standalone usage
if __name__ == "__main__":
    print("Testing ElevenLabsOutput module...")
    tts = ElevenLabsOutput()
    
    if tts.api_key:
        print("\nAPI key found - testing speech synthesis...")
        
        # Test basic speech synthesis
        success = tts.test_speech()
        if success:
            print("✅ Speech synthesis test completed successfully!")
        else:
            print("❌ Speech synthesis test failed.")
        
        # Test voice listing
        voices = tts.list_available_voices()
        if voices:
            print(f"\n📋 Found {len(voices)} available voices")
            print(f"🎤 Currently using voice: {tts.voice_id}")
        
    else:
        print("❌ No API key configured.")
        print("Please add your ElevenLabs API key to config.json")
        print("\nExample config.json structure:")
        print('{"elevenlabs": {"api_key": "your_api_key_here"}}')