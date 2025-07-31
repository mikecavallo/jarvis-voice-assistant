# 🤖 Jarvis Voice Assistant

A modular voice-controlled AI assistant built in Python, featuring advanced speech recognition, natural language processing, and high-quality text-to-speech synthesis.

## ✨ Features

- **🎤 Voice Control**: Wake word detection ("Jarvis") with continuous listening
- **🧠 Natural Language Processing**: Intelligent command parsing and execution
- **🔊 High-Quality TTS**: ElevenLabs integration for natural voice responses
- **📝 Persistent State**: JSON-based state management for goals, todos, and logs
- **🏗️ Modular Architecture**: Clean, extensible component-based design
- **🛠️ Multiple Modes**: Voice, text, and diagnostic test modes
- **⚡ Real-time Processing**: Asynchronous voice input with responsive feedback

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Microphone and speakers
- ElevenLabs API key (for voice output)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mikecavallo/jarvis-voice-assistant.git
   cd jarvis-voice-assistant
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API key:**
   - Get your ElevenLabs API key from [ElevenLabs](https://elevenlabs.io)
   - Update `config.json` with your API key:
   ```json
   {
     "elevenlabs": {
       "api_key": "your_api_key_here"
     }
   }
   ```

### Usage

**Voice Mode (Recommended):**
```bash
python main.py voice
```

**Text Mode (Command Line):**
```bash
python main.py text
```

**System Test:**
```bash
python main.py test
```

**Interactive Mode Selection:**
```bash
python main.py
```

## 🎯 Available Commands

- **Time & Date**: "What time is it?", "What's today's date?"
- **Web Browsing**: "Open browser", "Search Google for Python tutorials"
- **System Status**: "Status", "What are your goals?", "Show todos"
- **Help**: "Help", "What can you do?"
- **Control**: "Quit", "Goodbye"

## 🏗️ Architecture

### Core Components

- **`main.py`**: Application orchestrator and entry point
- **`voice_input.py`**: Speech recognition and wake word detection
- **`command_parser.py`**: Natural language command processing
- **`elevenlabs_output.py`**: Text-to-speech synthesis
- **`jarvis_state.py`**: Persistent state management
- **`config.py`**: Configuration management

### Design Patterns

- **Modular Architecture**: Each component is independent and reusable
- **Observer Pattern**: Voice input triggers command processing
- **State Management**: Centralized JSON-based persistence
- **Error Handling**: Comprehensive exception handling and recovery
- **Logging**: Detailed action logging for debugging

## 🛠️ Development

### Project Structure
```
jarvis-voice-assistant/
├── main.py                 # Application entry point
├── voice_input.py          # Speech recognition module
├── command_parser.py       # Command processing logic
├── elevenlabs_output.py    # Text-to-speech output
├── jarvis_state.py         # State management
├── config.py               # Configuration handling
├── config.json             # Configuration file
├── requirements.txt        # Python dependencies
├── jarvis_state.json       # Runtime state storage
└── README.md              # This file
```

### Key Dependencies

- **speech_recognition**: Voice input processing
- **faster-whisper**: Local speech recognition
- **pygame**: Audio playback
- **requests**: ElevenLabs API integration
- **pathlib**: Modern file path handling

## 🎓 Learning Outcomes

This project demonstrates:

- **Advanced Python Architecture**: Modular design with clear separation of concerns
- **Real-time Audio Processing**: Speech recognition and synthesis
- **API Integration**: External service integration with error handling
- **State Management**: Persistent application state with JSON storage
- **Asynchronous Programming**: Threading for responsive user interaction
- **Error Handling**: Comprehensive exception management
- **Configuration Management**: Flexible system configuration
- **Documentation**: Professional code documentation and README

## 🔧 Configuration

### config.json Structure
```json
{
  "elevenlabs": {
    "api_key": "your_api_key_here",
    "voice_id": "21m00Tcm4TlvDq8ikWAM",
    "model_id": "eleven_monolingual_v1"
  },
  "speech_recognition": {
    "engine": "whisper",
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
```

## 🚨 Troubleshooting

### Common Issues

**Microphone not detected:**
- Check microphone permissions
- Verify audio drivers are installed
- Run `python main.py test` for diagnostics

**ElevenLabs API errors:**
- Verify API key in config.json
- Check internet connection
- Ensure API quota is available

**Voice recognition issues:**
- Check microphone sensitivity
- Reduce background noise
- Try different speech recognition engines

## 🤝 Contributing

This is a learning project, but suggestions and improvements are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- **ElevenLabs** for high-quality text-to-speech API
- **OpenAI Whisper** for local speech recognition
- **Python Speech Recognition** library for audio processing
- **Pygame** for audio playbook capabilities

---

**Built with ❤️ for learning advanced Python architecture and AI integration**