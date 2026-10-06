#!/usr/bin/env python3
"""
Comprehensive transcription testing script to diagnose audio issues.

Tests different speech recognition engines with various configurations
to identify the best settings and troubleshoot audio problems.
"""

import speech_recognition as sr
import tempfile
import os
import sys
from datetime import datetime
from faster_whisper import WhisperModel
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
os.environ['ALSA_PCM_CARD'] = '0'
os.environ['ALSA_PCM_DEVICE'] = '0'

class TranscriptionTester:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.whisper_models = {}
        
    def find_microphone(self):
        """Find and configure the best microphone."""
        print("🎤 Testing microphone configurations...")
        
        configs = [
            {"device_index": None},
            {"device_index": 0},
            {"device_index": None, "sample_rate": 44100},
            {"device_index": None, "sample_rate": 22050},
            {"device_index": None, "sample_rate": 16000},
        ]
        
        for i, config in enumerate(configs):
            try:
                mic = sr.Microphone(**config)
                with mic as source:
                    pass
                print(f"✅ Config {i+1} works: {config}")
                self.microphone = mic
                return True
            except Exception as e:
                print(f"❌ Config {i+1} failed: {config} - {e}")
        
        return False
    
    def calibrate_microphone(self, duration=1):
        """Calibrate microphone for ambient noise."""
        if not self.microphone:
            return False
            
        try:
            with self.microphone as source:
                print(f"🔧 Calibrating microphone for {duration}s... stay quiet.")
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
                print(f"✅ Energy threshold set to: {self.recognizer.energy_threshold}")
                return True
        except Exception as e:
            print(f"❌ Calibration failed: {e}")
            return False
    
    def record_audio(self, timeout=10, phrase_limit=3):
        """Record audio with specified settings."""
        if not self.microphone:
            return None
            
        try:
            with self.microphone as source:
                print(f"🔴 Recording... (timeout: {timeout}s, phrase limit: {phrase_limit}s)")
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_limit
                )
                print(f"✅ Audio recorded: {len(audio.get_raw_data())} bytes")
                return audio
        except sr.WaitTimeoutError:
            print("⏰ Recording timeout - no speech detected")
            return None
        except Exception as e:
            print(f"❌ Recording failed: {e}")
            return None
    
    def test_google_recognition(self, audio_data):
        """Test Google Speech Recognition."""
        if not audio_data:
            return None
            
        print("\n🔍 Testing Google Speech Recognition...")
        try:
            text = self.recognizer.recognize_google(audio_data)
            print(f"✅ Google result: '{text}'")
            return text
        except sr.UnknownValueError:
            print("❌ Google: Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"❌ Google: Service error - {e}")
            return None
    
    def load_whisper_model(self, model_size="base"):
        """Load Whisper model if not already loaded."""
        if model_size not in self.whisper_models:
            try:
                print(f"📥 Loading Whisper {model_size} model...")
                model = WhisperModel(model_size, device="cpu", compute_type="int8")
                self.whisper_models[model_size] = model
                print(f"✅ Whisper {model_size} model loaded")
            except Exception as e:
                print(f"❌ Failed to load Whisper {model_size}: {e}")
                return None
        
        return self.whisper_models[model_size]
    
    def test_whisper_recognition(self, audio_data, model_size="base"):
        """Test Whisper recognition with different settings."""
        if not audio_data:
            return None
            
        model = self.load_whisper_model(model_size)
        if not model:
            return None
            
        print(f"\n🔍 Testing Whisper {model_size} recognition...")
        
        try:
            # Convert to WAV
            wav_data = audio_data.get_wav_data(convert_rate=16000, convert_width=2)
            
            # Create temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(wav_data)
                tmp_file_path = tmp_file.name
            
            try:
                # Test basic transcription
                segments, info = model.transcribe(tmp_file_path, language="en")
                text = " ".join([segment.text for segment in segments]).strip()
                
                print(f"✅ Whisper {model_size} result: '{text}'")
                print(f"   Duration: {info.duration:.1f}s")
                print(f"   Language confidence: {info.language_probability:.2f}")
                
                # Test with VAD
                segments_vad, info_vad = model.transcribe(
                    tmp_file_path, 
                    language="en",
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )
                text_vad = " ".join([segment.text for segment in segments_vad]).strip()
                
                print(f"✅ Whisper {model_size} with VAD: '{text_vad}'")
                print(f"   Duration with VAD: {info_vad.duration:.1f}s")
                
                return text, text_vad
                
            finally:
                os.unlink(tmp_file_path)
                
        except Exception as e:
            print(f"❌ Whisper {model_size} failed: {e}")
            return None
    
    def run_comprehensive_test(self):
        """Run comprehensive transcription tests."""
        print("=" * 60)
        print("🧪 COMPREHENSIVE TRANSCRIPTION TEST")
        print("=" * 60)
        
        # Test 1: Microphone setup
        if not self.find_microphone():
            print("❌ No working microphone found!")
            return
        
        # Test 2: Basic calibration
        if not self.calibrate_microphone():
            print("❌ Microphone calibration failed!")
            return
        
        # Test 3: Record test audio
        print("\n" + "="*50)
        print("🎤 AUDIO RECORDING TEST")
        print("Please say: 'What is the price of ethereum?'")
        print("="*50)
        
        audio = self.record_audio(timeout=5, phrase_limit=3)
        if not audio:
            print("❌ No audio recorded!")
            return
        
        # Test 4: Try different recognition methods
        results = {}
        
        # Google recognition
        google_result = self.test_google_recognition(audio)
        results['google'] = google_result
        
        # Whisper models
        for model_size in ['base', 'small']:
            whisper_results = self.test_whisper_recognition(audio, model_size)
            if whisper_results:
                results[f'whisper_{model_size}'] = whisper_results[0]
                results[f'whisper_{model_size}_vad'] = whisper_results[1]
        
        # Test 5: Summary
        print("\n" + "="*60)
        print("📊 TRANSCRIPTION RESULTS SUMMARY")
        print("="*60)
        print(f"Expected: 'What is the price of ethereum?'")
        print("-" * 40)
        
        for method, result in results.items():
            if result:
                print(f"{method:20}: {result}")
            else:
                print(f"{method:20}: FAILED")
        
        print("\n🔧 RECOMMENDATIONS:")
        
        # Check for repetition issues
        repeated_methods = []
        for method, result in results.items():
            if result and len(result.split()) > 10:
                repeated_methods.append(method)
        
        if repeated_methods:
            print(f"⚠️  Repetition detected in: {', '.join(repeated_methods)}")
            print("   - Possible microphone feedback or echo")
            print("   - Try using headphones or moving away from speakers")
        
        # Check accuracy
        target = "what is the price of ethereum"
        best_method = None
        best_score = 0
        
        for method, result in results.items():
            if result:
                # Simple word matching score
                result_words = result.lower().split()
                target_words = target.split()
                matches = sum(1 for word in target_words if word in result_words)
                score = matches / len(target_words)
                
                if score > best_score:
                    best_score = score
                    best_method = method
        
        if best_method:
            print(f"🏆 Best result: {best_method} (score: {best_score:.2f})")
        else:
            print("❌ No method produced good results")
    
    def interactive_test(self):
        """Interactive testing mode."""
        if not self.find_microphone():
            print("❌ No working microphone found!")
            return
        
        if not self.calibrate_microphone():
            print("❌ Microphone calibration failed!")
            return
        
        print("\n🎤 INTERACTIVE TRANSCRIPTION TEST")
        print("Commands:")
        print("  'test' - Record and transcribe")
        print("  'google' - Test Google recognition")
        print("  'whisper' - Test Whisper recognition") 
        print("  'quit' - Exit")
        
        while True:
            command = input("\ntest> ").strip().lower()
            
            if command == 'quit':
                break
            elif command == 'test':
                audio = self.record_audio(timeout=5, phrase_limit=3)
                if audio:
                    self.test_google_recognition(audio)
                    self.test_whisper_recognition(audio)
            elif command == 'google':
                audio = self.record_audio(timeout=5, phrase_limit=3)
                if audio:
                    self.test_google_recognition(audio)
            elif command == 'whisper':
                audio = self.record_audio(timeout=5, phrase_limit=3)
                if audio:
                    self.test_whisper_recognition(audio)
            else:
                print("Unknown command. Try 'test', 'google', 'whisper', or 'quit'")

def main():
    """Main function."""
    tester = TranscriptionTester()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'interactive':
        tester.interactive_test()
    else:
        tester.run_comprehensive_test()

if __name__ == "__main__":
    main()