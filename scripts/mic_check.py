#!/usr/bin/env python3
"""
Simple audio recording and playback test to isolate audio issues.
"""

import speech_recognition as sr
import wave
import os
import tempfile

def test_basic_recording():
    """Test basic audio recording and save to file."""
    print("🎤 Basic Audio Recording Test")
    print("=" * 40)
    
    recognizer = sr.Recognizer()
    
    # Try to find a working microphone
    try:
        mic = sr.Microphone()
        print("✅ Microphone initialized")
    except Exception as e:
        print(f"❌ Microphone failed: {e}")
        return
    
    # Record audio
    try:
        with mic as source:
            print("📏 Adjusting for ambient noise... (2 seconds)")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            print(f"🔊 Energy threshold: {recognizer.energy_threshold}")
            
            print("\n🔴 Recording 3 seconds of audio...")
            print("📢 Please say: 'Hello, this is a test'")
            
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=3)
            print(f"✅ Recorded {len(audio.get_raw_data())} bytes")
            
    except Exception as e:
        print(f"❌ Recording failed: {e}")
        return
    
    # Save audio to file for inspection
    try:
        wav_data = audio.get_wav_data()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_data)
            temp_path = f.name
        
        print(f"💾 Audio saved to: {temp_path}")
        print("   You can play this file to hear what was recorded")
        
        # Try basic Google recognition
        try:
            text = recognizer.recognize_google(audio)
            print(f"🔍 Google recognized: '{text}'")
        except sr.UnknownValueError:
            print("❌ Google could not understand the audio")
        except Exception as e:
            print(f"❌ Google recognition error: {e}")
        
        # Show file info
        try:
            with wave.open(temp_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                duration = frames / sample_rate
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                
                print(f"\n📊 Audio file details:")
                print(f"   Duration: {duration:.1f} seconds")
                print(f"   Sample rate: {sample_rate} Hz")
                print(f"   Channels: {channels}")
                print(f"   Sample width: {sample_width} bytes")
        except Exception as e:
            print(f"❌ Could not read audio file: {e}")
            
    except Exception as e:
        print(f"❌ Could not save audio: {e}")

def main():
    test_basic_recording()

if __name__ == "__main__":
    main()