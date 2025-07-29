"""
ElevenLabs Voice Output Module for Jarvis Assistant.
Handles text-to-speech conversion and audio playback using ElevenLabs API.
"""

import os
import tempfile
import time
from typing import Optional
import pygame
import requests
from pathlib import Path
from config import config
from jarvis_state import jarvis_state

class ElevenLabsOutput:
    """Handles text-to-speech using ElevenLabs API and audio playback."""
    
    def __init__(self):
        """Initialize ElevenLabs output with API configuration."""
        self.api_key = config.get("elevenlabs", "api_key")
        self.voice_id = config.get("elevenlabs", "voice_id", "21m00Tcm4TlvDq8ikWAM")
        self.model_id = config.get("elevenlabs", "model_id", "eleven_monolingual_v1")
        self.base_url = "https://api.elevenlabs.io/v1"
        
        # Initialize pygame mixer for audio playback
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        
        # Validate API key
        if not self.api_key:
            print("Warning: ElevenLabs API key not found in config!")
            print("Please add your API key to config.json or set ELEVENLABS_API_KEY environment variable")
            jarvis_state.log_action("elevenlabs_no_key", "API key missing", "elevenlabs_output")
        else:
            jarvis_state.log_action("elevenlabs_initialized", f"Using voice ID: {self.voice_id}", "elevenlabs_output")
            # Test API connection
            self._test_api_connection()
    
    def _test_api_connection(self) -> bool:
        """Test connection to ElevenLabs API."""
        try:
            headers = {
                "Accept": "application/json",
                "xi-api-key": self.api_key
            }
            
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
    
    def speak(self, text: str, save_audio: bool = False) -> bool:
        """
        Convert text to speech and play it.
        
        Args:
            text: Text to convert to speech
            save_audio: Whether to save the audio file
            
        Returns:
            True if successful, False otherwise
        """
        if not text or not text.strip():
            return False
        
        if not self.api_key:
            print(f"Text-to-speech disabled (no API key): {text}")
            return False
        
        jarvis_state.log_action("tts_request", f"Speaking: {text[:50]}...", "elevenlabs_output")
        
        try:
            # Generate speech from ElevenLabs
            audio_data = self._generate_speech(text)
            if not audio_data:
                return False
            
            # Save to temporary file and play
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
        
        Args:
            text: Text to convert
            
        Returns:
            Audio data as bytes or None if failed
        """
        try:
            url = f"{self.base_url}/text-to-speech/{self.voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": self.model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.content
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
        Play audio data using pygame.
        
        Args:
            audio_data: Audio bytes to play
            save_filename: Optional filename to save audio
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # Load and play the audio
                pygame.mixer.music.load(temp_file_path)
                pygame.mixer.music.play()
                
                # Wait for playback to complete
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                
                # Save audio if requested
                if save_filename:
                    save_path = Path("audio_output") / f"{save_filename}.mp3"
                    save_path.parent.mkdir(exist_ok=True)
                    with open(save_path, 'wb') as f:
                        f.write(audio_data)
                    print(f"Audio saved to: {save_path}")
                
                return True
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"Error playing audio: {e}")
            return False
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Change the voice used for speech synthesis.
        
        Args:
            voice_id: ElevenLabs voice ID
            
        Returns:
            True if voice is valid, False otherwise
        """
        try:
            # Test the voice by getting voice info
            headers = {
                "Accept": "application/json",
                "xi-api-key": self.api_key
            }
            
            response = requests.get(f"{self.base_url}/voices/{voice_id}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.voice_id = voice_id
                config.set("elevenlabs", "voice_id", voice_id)
                jarvis_state.log_action("voice_changed", f"Voice changed to: {voice_id}", "elevenlabs_output")
                return True
            else:
                print(f"Invalid voice ID: {voice_id}")
                return False
                
        except Exception as e:
            print(f"Error setting voice: {e}")
            return False
    
    def list_available_voices(self) -> Optional[dict]:
        """
        Get list of available voices from ElevenLabs.
        
        Returns:
            Dictionary of voice information or None if failed
        """
        try:
            headers = {
                "Accept": "application/json",
                "xi-api-key": self.api_key
            }
            
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
        Test the speech synthesis system.
        
        Args:
            test_text: Text to use for testing
            
        Returns:
            True if test successful, False otherwise
        """
        print(f"Testing speech synthesis with: '{test_text}'")
        return self.speak(test_text)
    
    def stop_playback(self):
        """Stop any currently playing audio."""
        try:
            pygame.mixer.music.stop()
            jarvis_state.log_action("playback_stopped", "Audio playback stopped", "elevenlabs_output")
        except Exception as e:
            print(f"Error stopping playback: {e}")

# Test function for standalone usage
if __name__ == "__main__":
    tts = ElevenLabsOutput()
    
    # Test the system
    if tts.api_key:
        print("Testing ElevenLabs speech synthesis...")
        success = tts.test_speech()
        if success:
            print("Speech test completed successfully!")
        else:
            print("Speech test failed.")
    else:
        print("No API key configured. Please set up your ElevenLabs API key in config.json")