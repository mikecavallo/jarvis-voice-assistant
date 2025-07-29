"""
Voice Input Module for Jarvis Assistant.
Handles microphone input and speech-to-text conversion using multiple engines.
"""

import speech_recognition as sr
import threading
import time
from typing import Optional, Callable
from faster_whisper import WhisperModel
from config import config
from jarvis_state import jarvis_state

class VoiceInput:
    """Handles voice input and speech recognition for Jarvis."""
    
    def __init__(self):
        """Initialize voice input with configured recognition engine."""
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        self.wake_word = config.get("general", "wake_word", "jarvis").lower()
        
        # Initialize Whisper model if using whisper engine
        self.whisper_model = None
        if config.get("speech_recognition", "engine") == "whisper":
            try:
                # Initialize with small model for faster processing
                self.whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
                jarvis_state.log_action("whisper_initialized", "Whisper model loaded successfully", "voice_input")
            except Exception as e:
                jarvis_state.log_action("whisper_error", f"Failed to load Whisper: {e}", "voice_input")
                print(f"Warning: Could not load Whisper model: {e}")
                print("Falling back to Google Speech Recognition")
        
        # Calibrate microphone for ambient noise
        self._calibrate_microphone()
    
    def _calibrate_microphone(self):
        """Calibrate microphone for ambient noise levels."""
        try:
            with self.microphone as source:
                print("Calibrating microphone for ambient noise... Please stay quiet.")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                print("Microphone calibrated!")
                jarvis_state.log_action("mic_calibrated", "Microphone calibrated for ambient noise", "voice_input")
        except Exception as e:
            print(f"Warning: Could not calibrate microphone: {e}")
            jarvis_state.log_action("mic_calibration_failed", str(e), "voice_input")
    
    def listen_for_wake_word(self, callback: Callable[[str], None]) -> None:
        """
        Continuously listen for the wake word, then capture command.
        
        Args:
            callback: Function to call with recognized speech
        """
        print(f"Listening for wake word: '{self.wake_word}'...")
        self.is_listening = True
        
        while self.is_listening:
            try:
                with self.microphone as source:
                    # Listen for wake word with shorter timeout
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                
                # Quick recognition for wake word detection
                try:
                    text = self._recognize_speech(audio, quick=True)
                    if text and self.wake_word in text.lower():
                        print(f"Wake word detected! Listening for command...")
                        jarvis_state.log_action("wake_word_detected", f"Detected: {text}", "voice_input")
                        
                        # Now listen for the actual command
                        command = self.listen_for_command()
                        if command:
                            callback(command)
                        
                except sr.UnknownValueError:
                    # No speech detected, continue listening
                    continue
                except sr.RequestError as e:
                    print(f"Speech recognition service error: {e}")
                    time.sleep(1)
                    
            except sr.WaitTimeoutError:
                # Timeout is expected when continuously listening
                continue
            except Exception as e:
                print(f"Error in wake word detection: {e}")
                jarvis_state.log_action("wake_word_error", str(e), "voice_input")
                time.sleep(1)
    
    def listen_for_command(self, timeout: int = 5) -> Optional[str]:
        """
        Listen for a voice command after wake word is detected.
        
        Args:
            timeout: Maximum time to wait for command
            
        Returns:
            Recognized text or None if no speech detected
        """
        try:
            with self.microphone as source:
                print("Listening for command...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
            
            # Use more accurate recognition for commands
            text = self._recognize_speech(audio, quick=False)
            if text:
                print(f"Command received: {text}")
                jarvis_state.log_action("command_received", text, "voice_input")
                return text
            else:
                print("No command detected")
                return None
                
        except sr.WaitTimeoutError:
            print("No command received within timeout")
            return None
        except Exception as e:
            print(f"Error recognizing command: {e}")
            jarvis_state.log_action("command_recognition_error", str(e), "voice_input")
            return None
    
    def _recognize_speech(self, audio_data, quick: bool = False) -> Optional[str]:
        """
        Convert audio to text using configured recognition engine.
        
        Args:
            audio_data: Audio data from microphone
            quick: If True, use faster but less accurate recognition
            
        Returns:
            Recognized text or None
        """
        engine = config.get("speech_recognition", "engine", "google")
        
        try:
            if engine == "whisper" and self.whisper_model and not quick:
                return self._recognize_with_whisper(audio_data)
            else:
                # Use Google Speech Recognition (online service)
                return self._recognize_with_google(audio_data)
        except Exception as e:
            print(f"Recognition error: {e}")
            return None
    
    def _recognize_with_google(self, audio_data) -> Optional[str]:
        """Recognize speech using Google Speech Recognition API."""
        try:
            language = config.get("speech_recognition", "language", "en-US")
            text = self.recognizer.recognize_google(audio_data, language=language)
            return text
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"Google Speech Recognition error: {e}")
            return None
    
    def _recognize_with_whisper(self, audio_data) -> Optional[str]:
        """Recognize speech using Whisper model."""
        try:
            # Convert audio data to wav format for Whisper
            wav_data = audio_data.get_wav_data()
            
            # Save temporarily for Whisper processing
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(wav_data)
                tmp_file_path = tmp_file.name
            
            try:
                # Transcribe with Whisper
                segments, info = self.whisper_model.transcribe(tmp_file_path, beam_size=5)
                text = " ".join([segment.text for segment in segments]).strip()
                return text if text else None
            finally:
                # Clean up temporary file
                os.unlink(tmp_file_path)
                
        except Exception as e:
            print(f"Whisper recognition error: {e}")
            return None
    
    def start_listening_async(self, callback: Callable[[str], None]):
        """Start listening in a separate thread."""
        if not self.is_listening:
            self.listening_thread = threading.Thread(
                target=self.listen_for_wake_word, 
                args=(callback,),
                daemon=True
            )
            self.listening_thread.start()
            jarvis_state.log_action("listening_started", "Voice input thread started", "voice_input")
    
    def stop_listening(self):
        """Stop the listening loop."""
        self.is_listening = False
        jarvis_state.log_action("listening_stopped", "Voice input stopped", "voice_input")
        print("Voice input stopped.")
    
    def test_microphone(self) -> bool:
        """Test if microphone is working properly."""
        try:
            with self.microphone as source:
                print("Testing microphone... Say something!")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=3)
            
            text = self._recognize_speech(audio)
            if text:
                print(f"Microphone test successful! Heard: {text}")
                return True
            else:
                print("Microphone test failed: No speech detected")
                return False
                
        except Exception as e:
            print(f"Microphone test failed: {e}")
            return False

# Test function for standalone usage
if __name__ == "__main__":
    def test_callback(command):
        print(f"Received command: {command}")
    
    voice = VoiceInput()
    
    # Test microphone first
    if voice.test_microphone():
        print("Starting voice input test...")
        voice.listen_for_wake_word(test_callback)