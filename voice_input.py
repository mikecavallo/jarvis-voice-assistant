"""
Voice Input Module for Jarvis Assistant.

This module handles all aspects of voice input including:
- Microphone configuration and calibration
- Wake word detection
- Voice command recognition
- Multiple speech recognition engines (Google, Whisper)
- Audio error handling and recovery

The module is designed to be robust and handle various audio hardware configurations
while providing fallback options when primary methods fail.
"""

import speech_recognition as sr
import threading
import time
import tempfile
import os
import warnings
from contextlib import redirect_stderr
from typing import Optional, Callable
from faster_whisper import WhisperModel
from config import config
from memory.state_manager import jarvis_state

# Suppress audio warnings
warnings.filterwarnings('ignore', category=UserWarning)
# Let system choose audio device automatically


class VoiceInput:
    """
    Handles voice input and speech recognition for Jarvis Assistant.
    
    This class manages the complete voice input pipeline:
    1. Microphone hardware detection and configuration
    2. Wake word detection ("jarvis" by default)  
    3. Command listening and processing
    4. Speech-to-text conversion using multiple engines
    
    Attributes:
        recognizer (sr.Recognizer): SpeechRecognition recognizer instance
        microphone (sr.Microphone): Configured microphone object
        is_listening (bool): Flag indicating if actively listening
        wake_word (str): Configured wake word (default: "jarvis")
        whisper_model (WhisperModel): Local Whisper model instance (optional)
    """
    
    def __init__(self):
        """
        Initialize voice input with optimal microphone configuration.
        
        Sets up speech recognition, finds the best microphone configuration,
        optionally loads Whisper model, and calibrates for ambient noise.
        """
        self.recognizer = sr.Recognizer()
        self.microphone = self._find_optimal_microphone()
        self.is_listening = False
        self.wake_word = config.get("general", "wake_word", "jarvis").lower()
        self.use_vad = config.get("speech_recognition", "use_voice_activity_detection", True)
        
        # Initialize Whisper model if configured
        self.whisper_model = self._initialize_whisper()
        
        # Calibrate microphone for ambient noise
        self._calibrate_microphone()
    
    def _find_optimal_microphone(self) -> sr.Microphone:
        """
        Find the best working microphone configuration.
        
        Tries multiple configurations in order of preference:
        1. Default system microphone
        2. First available device
        3. Device with specific sample rates
        
        Returns:
            sr.Microphone: Configured microphone object
        """
        # Configuration options in order of preference (robust fallbacks)
        configs = [
            {"device_index": None},                          # System default (let system choose)
            {"device_index": 0},                             # First device
            {"device_index": None, "sample_rate": 44100},    # System default with common rate
            {"device_index": None, "sample_rate": 22050},    # System default with lower rate
            {"device_index": None, "sample_rate": 16000},    # System default with Whisper rate
            {"device_index": 0, "sample_rate": 44100},       # First device with common rate
            {"device_index": 0, "sample_rate": 22050},       # First device with lower rate
            {"device_index": 0, "sample_rate": 16000},       # First device with Whisper rate
        ]
        
        for config_dict in configs:
            try:
                # Suppress ALSA errors during microphone testing
                with redirect_stderr(open(os.devnull, 'w')):
                    mic = sr.Microphone(**config_dict)
                    # Test if microphone can be opened
                    with mic as source:
                        # Quick test to ensure it works
                        source.CHUNK = 1024  # Smaller chunk size for compatibility
                
                print(f"✅ Using microphone config: {config_dict}")
                jarvis_state.log_action("mic_config_found", f"Config: {config_dict}", "voice_input")
                return mic
            except Exception as e:
                print(f"⚠️  Config {config_dict} failed: {e}")
                continue
        
        # Fallback to basic configuration
        print("⚠️  Using fallback microphone configuration")
        return sr.Microphone()
    
    def _initialize_whisper(self) -> Optional[WhisperModel]:
        """
        Initialize Whisper model if configured.
        
        Returns:
            WhisperModel: Initialized Whisper model or None if disabled/failed
        """
        if config.get("speech_recognition", "engine") != "whisper":
            return None
            
        try:
            # Use medium model for much better accuracy (larger but more accurate)
            model = WhisperModel("medium", device="cpu", compute_type="int8")
            print("✅ Whisper medium model loaded successfully!")
            jarvis_state.log_action("whisper_initialized", "Whisper medium model loaded", "voice_input")
            return model
        except Exception as e:
            jarvis_state.log_action("whisper_error", f"Failed to load Whisper: {e}", "voice_input")
            print(f"Warning: Could not load Whisper model: {e}")
            print("Falling back to Google Speech Recognition")
            return None
    
    def _calibrate_microphone(self):
        """
        Calibrate microphone for ambient noise and set optimal sensitivity.
        
        This method:
        1. Adjusts for background noise
        2. Sets energy threshold for better sensitivity
        3. Configures pause detection timing
        """
        try:
            with self.microphone as source:
                print("Calibrating microphone for optimal speech recognition... Please stay quiet for 2 seconds.")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)  # Longer calibration
                
                # Optimize sensitivity settings for cleaner audio capture
                self.recognizer.energy_threshold = 300        # Higher threshold to avoid background noise
                self.recognizer.dynamic_energy_threshold = True  # Adapt to changing conditions
                self.recognizer.pause_threshold = 0.8         # Shorter pause to stop recording sooner
                self.recognizer.non_speaking_duration = 0.5   # Stop recording sooner after silence
                self.recognizer.phrase_threshold = 0.3        # Minimum phrase length
                
                print("✅ Microphone calibrated for high-accuracy speech recognition!")
                jarvis_state.log_action("mic_calibrated", "Microphone calibrated for accuracy", "voice_input")
        except Exception as e:
            print(f"Warning: Could not calibrate microphone: {e}")
            jarvis_state.log_action("mic_calibration_failed", str(e), "voice_input")
    
    def listen_for_wake_word(self, callback: Callable[[str], None]) -> None:
        """
        Continuously listen for the wake word, then process commands.
        
        This is the main listening loop that:
        1. Listens for the configured wake word
        2. When detected, switches to command listening mode
        3. Processes the command and calls the callback function
        
        Args:
            callback: Function to call with recognized command text
        """
        print(f"Listening for wake word: '{self.wake_word}'...")
        self.is_listening = True
        
        while self.is_listening:
            try:
                with self.microphone as source:
                    # Short timeout for responsive wake word detection
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                
                # Quick recognition for wake word detection
                text = self._recognize_speech(audio, quick=True)
                if text and self.wake_word in text.lower():
                    print(f"Wake word detected! Listening for command...")
                    jarvis_state.log_action("wake_word_detected", f"Detected: {text}", "voice_input")
                    
                    # Switch to command listening mode
                    command = self.listen_for_command()
                    if command:
                        callback(command)
                        
            except sr.UnknownValueError:
                # No speech detected - continue listening
                continue
            except sr.WaitTimeoutError:
                # Timeout is expected during continuous listening
                continue
            except sr.RequestError as e:
                print(f"Speech recognition service error: {e}")
                time.sleep(1)
            except Exception as e:
                print(f"Error in wake word detection: {e}")
                jarvis_state.log_action("wake_word_error", str(e), "voice_input")
                time.sleep(1)
    
    def listen_for_command(self, timeout: int = 15) -> Optional[str]:
        """
        Listen for a voice command after wake word detection.
        
        This method provides user feedback and captures the actual command
        with higher accuracy settings than wake word detection.
        
        Args:
            timeout: Maximum time to wait for command (seconds)
            
        Returns:
            str: Recognized command text, or None if no speech detected
        """
        try:
            print("🎤 Ready to listen for command...")
            if self.use_vad:
                print("💬 Speak now - I'll stop listening when you finish!")
            else:
                print(f"💬 Speak clearly within {timeout} seconds!")
            
            # Capture audio with error suppression
            with self.microphone as source:
                # Quick recalibration for command listening
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                
                print("🔴 Listening now...")
                if self.use_vad:
                    audio = self._listen_with_vad(source, timeout)
                    if audio is None:
                        return None
                else:
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=8)
                print("✅ Audio captured, processing...")
            
            # Use more accurate recognition for commands
            text = self._recognize_speech(audio, quick=False)
            if text:
                print(f"🎯 Command received: {text}")
                jarvis_state.log_action("command_received", text, "voice_input")
                return text
            else:
                print("❌ No command detected")
                return None
                
        except sr.WaitTimeoutError:
            print("⏰ No command received within timeout")
            return None
        except Exception as e:
            print(f"❌ Error recognizing command: {e}")
            jarvis_state.log_action("command_recognition_error", str(e), "voice_input")
            return None
    
    def _listen_with_vad(self, source, max_timeout: int = 15) -> Optional:
        """
        Listen with simplified voice activity detection.
        
        Args:
            source: Microphone source
            max_timeout: Maximum time to wait for speech to start
            
        Returns:
            Audio data or None if timeout/no speech
        """
        try:
            # Use SpeechRecognition's built-in pause detection optimized for accuracy
            original_pause = self.recognizer.pause_threshold
            self.recognizer.pause_threshold = 0.8  # Stop after 0.8 seconds of silence to avoid long recordings
            
            try:
                audio_data = self.recognizer.listen(
                    source, 
                    timeout=max_timeout,
                    phrase_time_limit=5  # Reduce to 5 seconds max per phrase
                )
                return audio_data
                
            finally:
                # Restore original pause threshold
                self.recognizer.pause_threshold = original_pause
                
        except sr.WaitTimeoutError:
            print("⏰ No speech detected")
            return None
        except Exception as e:
            print(f"❌ VAD error: {e}")
            # Fallback to regular listening
            try:
                return self.recognizer.listen(source, timeout=3, phrase_time_limit=8)
            except:
                return None
    
    def _recognize_speech(self, audio_data, quick: bool = False) -> Optional[str]:
        """
        Convert audio to text using the configured recognition engine.
        
        Args:
            audio_data: Audio data from microphone
            quick: If True, use faster but less accurate recognition
            
        Returns:
            str: Recognized text, or None if recognition failed
        """
        engine = config.get("speech_recognition", "engine", "google")
        
        try:
            if engine == "whisper" and self.whisper_model:
                # Always use Whisper when available and configured
                return self._recognize_with_whisper(audio_data)
            else:
                # Fallback to Google Speech Recognition
                return self._recognize_with_google(audio_data)
        except Exception as e:
            print(f"Recognition error: {e}")
            return None
    
    def _recognize_with_google(self, audio_data) -> Optional[str]:
        """
        Recognize speech using Google Speech Recognition API.
        
        Args:
            audio_data: Audio data from microphone
            
        Returns:
            str: Recognized text, or None if recognition failed
        """
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
        """
        Recognize speech using local Whisper model.
        
        Args:
            audio_data: Audio data from microphone
            
        Returns:
            str: Recognized text, or None if recognition failed
        """
        try:
            # Convert audio data to WAV format for Whisper with optimal settings
            # Use 16kHz sample rate which is optimal for Whisper
            try:
                wav_data = audio_data.get_wav_data(convert_rate=16000, convert_width=2)
            except:
                # Fallback: use original sample rate if conversion fails
                wav_data = audio_data.get_wav_data()
            
            # Create temporary file for Whisper processing
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(wav_data)
                tmp_file_path = tmp_file.name
            
            try:
                # Transcribe with Whisper using maximum accuracy settings
                segments, info = self.whisper_model.transcribe(
                    tmp_file_path, 
                    beam_size=10,  # Increased beam size for better accuracy
                    language="en",  # Force English for better accuracy
                    condition_on_previous_text=False,  # Prevent hallucination
                    temperature=0.0,  # Use greedy decoding for consistency
                    compression_ratio_threshold=2.4,  # Default threshold
                    log_prob_threshold=-1.0,  # Default threshold
                    no_speech_threshold=0.6,  # More conservative speech detection
                    word_timestamps=True,  # Enable word-level timestamps for better parsing
                    prepend_punctuations="\"'([{-",
                    append_punctuations="\"'.,!?:)]}",
                    vad_filter=True,  # Filter out background noise
                    vad_parameters=dict(
                        min_silence_duration_ms=800,  # Longer silence to stop processing sooner
                        speech_pad_ms=200,  # Less padding around speech
                    )
                )
                
                text = " ".join([segment.text for segment in segments]).strip()
                print(f"🔍 Whisper transcription: '{text}'")
                print(f"🔍 Whisper confidence: {info.language_probability:.2f}")
                print(f"🔍 Audio duration: {info.duration:.1f}s")
                
                # Check for repeated content (likely audio feedback/echo)
                words = text.split()
                if len(words) > 10:  # If more than 10 words
                    # Check if first few words repeat throughout
                    first_phrase = " ".join(words[:5])
                    if text.count(first_phrase) > 2:  # If phrase repeats more than twice
                        print("⚠️  Detected repeated audio - possible microphone feedback")
                        # Return only the first occurrence
                        text = first_phrase
                
                # If confidence is very low, warn but still return the text
                if info.language_probability < 0.5:
                    print("⚠️  Low confidence transcription - consider speaking more clearly")
                
                return text if text else None
            finally:
                # Clean up temporary file
                os.unlink(tmp_file_path)
                
        except Exception as e:
            print(f"Whisper recognition error: {e}")
            return None
    
    def start_listening_async(self, callback: Callable[[str], None]):
        """
        Start listening for wake word in a separate thread.
        
        Args:
            callback: Function to call with recognized commands
        """
        if not self.is_listening:
            self.listening_thread = threading.Thread(
                target=self.listen_for_wake_word, 
                args=(callback,),
                daemon=True
            )
            self.listening_thread.start()
            jarvis_state.log_action("listening_started", "Voice input thread started", "voice_input")
    
    def start_conversation_async(self, callback: Callable[[str], None]):
        """
        Start continuous conversation mode without wake words.
        
        Args:
            callback: Function to call with recognized commands
        """
        if not self.is_listening:
            self.listening_thread = threading.Thread(
                target=self.continuous_conversation, 
                args=(callback,),
                daemon=True
            )
            self.listening_thread.start()
            jarvis_state.log_action("conversation_started", "Continuous conversation started", "voice_input")
    
    def continuous_conversation(self, callback: Callable[[str], None]):
        """
        Continuous conversation loop without wake words.
        
        Args:
            callback: Function to call with recognized commands
        """
        self.is_listening = True
        print("🎤 Continuous conversation mode active")
        
        while self.is_listening:
            try:
                print("🔴 Listening for command...")
                
                # Listen for command directly
                command = self.listen_for_command()
                
                if command:
                    # Check for stop commands
                    if any(stop in command.lower() for stop in ["goodbye", "stop", "quit", "exit"]):
                        print("👋 Conversation ending...")
                        callback(command)  # Let main handle shutdown
                        break
                    
                    # Process normal command
                    callback(command)
                    
                    # Brief pause
                    time.sleep(0.5)
                else:
                    # No command detected, continue listening
                    print("❓ No command detected. Continuing to listen...")
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Conversation error: {e}")
                time.sleep(1)
    
    def stop_listening(self):
        """Stop the listening loop and clean up resources."""
        self.is_listening = False
        jarvis_state.log_action("listening_stopped", "Voice input stopped", "voice_input")
        print("Voice input stopped.")
    
    def test_microphone(self) -> bool:
        """
        Test microphone functionality with a simple recording test.
        
        Returns:
            bool: True if microphone test successful, False otherwise
        """
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


# Module test function
if __name__ == "__main__":
    def test_callback(command):
        """Test callback function for standalone testing."""
        print(f"Received command: {command}")
    
    print("Testing VoiceInput module...")
    voice = VoiceInput()
    
    # Test microphone first
    if voice.test_microphone():
        print("Starting voice input test...")
        voice.listen_for_wake_word(test_callback)
    else:
        print("Microphone test failed. Please check your audio setup.")