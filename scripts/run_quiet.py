#!/usr/bin/env python3
"""
Quiet wrapper for Jarvis that suppresses ALSA warnings while preserving important output.
"""

import os
import sys
import subprocess
import select
import threading
import time

def should_suppress_line(line):
    """Check if a line should be suppressed."""
    suppress_patterns = [
        "ALSA lib",
        "Cannot connect to server socket",
        "Cannot connect to server request channel",
        "jack server is not running",
        "JackShmReadWritePtr",
        "libasound_module_pcm_pulse.so", 
        "Failed to send telemetry event",
        "dlobj_cache_get0",  # ALSA library loading errors
    ]
    
    # Don't suppress important Jarvis messages
    important_patterns = [
        "🎯 Command received:",
        "🎯 Processing command:",
        "💬 Response:",
        "🔴 Listening",
        "✅ Audio captured", 
        "🎤",
        "🤖 Jarvis:",
        "User:",
        "🔍 DEBUG:",  # Debug messages
    ]
    
    # Always keep important messages
    for important in important_patterns:
        if important in line:
            return False
    
    # Suppress known noise
    for pattern in suppress_patterns:
        if pattern in line:
            return True
    return False

def run_with_filtered_output(command):
    """Run command and filter out ALSA warnings while preserving other output."""
    
    # Set environment variables to reduce ALSA verbosity
    env = os.environ.copy()
    env.update({
        'PYGAME_HIDE_SUPPORT_PROMPT': '1',
        'ALSA_PCM_CARD': '0',
        'ALSA_PCM_DEVICE': '0', 
        'ANONYMIZED_TELEMETRY': 'False',
        'SDL_AUDIODRIVER': 'alsa',  # Direct ALSA to avoid PulseAudio errors
    })
    
    # Start the process
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
        env=env
    )
    
    # Process output line by line with better real-time display
    try:
        import sys
        for line in iter(process.stdout.readline, ''):
            if line.strip() and not should_suppress_line(line):
                # Force immediate output
                print(line, end='')
                sys.stdout.flush()
        
        process.wait()
        return process.returncode
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping Jarvis...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        return 130

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_quiet.py <command> [args...]")
        sys.exit(1)
    
    # Pass through all arguments
    command = sys.argv[1:]
    exit_code = run_with_filtered_output(command)
    sys.exit(exit_code)