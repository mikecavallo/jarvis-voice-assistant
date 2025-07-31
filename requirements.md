# Jarvis Voice Assistant — Project Requirements Document

## 📘 Overview

Jarvis is a Python-based, voice-controlled AI assistant designed to run on a GPU-powered machine as a long-term project-based learning solution. It will be developed incrementally using Claude Code CLI and Gemini Code CLI. The assistant will be modular, extensible, and entirely voice-driven.

The primary goals are:

- Improve the developer’s Python, Git, and system integration skills
- Develop a fully functional Jarvis-like assistant capable of executing system and API commands
- Build and extend Jarvis in daily modular feature additions

---

## 🔰 MVP Scope (Phase 1: Bare Bones Jarvis)

### ✅ Features

- Voice input via local Whisper (using `faster-whisper` for GPU acceleration)
- Basic voice command recognition (e.g., "open browser", "what time is it", etc.)
- Voice output using ElevenLabs API
- Shared JSON state file (`jarvis_state.json`) for managing:
  - Goals
  - Todo list
  - Log of actions
  - Current task ownership by Claude or Gemini
- Modular codebase with clear explanations and Git commit messages
- Local Git repo initialized with clean structure and proper `.gitignore`

### 🧱 File Structure

```
jarvis-assistant/
├── main.py
├── config.py
├── voice_input.py
├── command_parser.py
├── elevenlabs_output.py
├── jarvis_state.json
├── tools/
├── logs/
├── requirements.txt
└── README.md
```

---

## 🚀 Phase 2: Intermediate Features

### 🧠 Conversational Capabilities

- Local vector store memory (e.g., FAISS or ChromaDB)
- Context tracking and recall from prior sessions
- Personality development through memory and reflection logs

### 🧰 Tool & API Integrations

- Modular MCP (Model Context Protocol) tool runner
- Weather API
- Google Calendar integration
- File summarization (read PDF, DOCX, TXT via voice)
- Email assistant (send, read, summarize)
- Web search via Gemini

### 🛠️ System Automation

- Open/close applications via voice
- Cleanup temporary files
- Voice macros (e.g., for gaming or app control)
- Control brightness, volume, etc.

---

## 🧠 Phase 3: Advanced Intelligence & Autonomy

### 🔁 Planning & Organizational Features

- Self-generated daily task plans
- Standup assistant: "What are you working on today, Jarvis?"
- Feature review summaries
- Auto-documentation of features
- Changelog generation

### 📷 Visual Context & Copilot Mode

- Run as background service, always listening for trigger word
- Capture screenshots on-demand ("Hey Jarvis, how do I change this?")
- Annotate or analyze screenshots with OCR and context
- Contextual help depending on active app

### 📈 Learning Tools

- Track which AI agent contributed what
- Explain a function or feature on request ("Explain this function")
- Debugging assistant: find bugs in live code
- Reflective mode: Jarvis critiques and suggests better approaches

---

## 🔒 Security & Privacy

- All voice logs and memory are stored locally
- Optional encryption for memory and state files
- Kill switch command: "Jarvis, shut everything down"

---

## 📦 Dependencies & Stack

- Python 3.10+
- `faster-whisper`
- `pyaudio` or `sounddevice` (for mic input)
- `requests` (for API calls)
- `pyttsx3` (optional offline TTS fallback)
- ElevenLabs API key (voice output)
- Git, GitHub (version control)
- Claude Code CLI & Gemini Code CLI (dev partners)

---

## 🧪 Development Philosophy

- Claude and Gemini should not just generate code—they must explain what they write and why
- Each new feature must be:
  1. Explained clearly (line-by-line or file-by-file)
  2. Git committed with a clean message
  3. Added to `jarvis_state.json` with status updates

---

## 🗺️ Final Vision

Jarvis will:

- Run persistently in the background
- Communicate naturally with the user via voice
- Help with real-world tasks across any application
- Learn and improve from conversations
- Become a true desktop copilot

please output to a .md file

