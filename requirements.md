# Jarvis Virtual Assistant — Comprehensive Product Requirements Document
*Generated 2025-08-05*

---

## 1. Vision & Scope

Build a modular, voice-first personal AI assistant ("**Jarvis**") that can:

1. **Converse naturally** through speech on the local machine (CLI)
2. **Access a central MCP server** for all external tools & APIs
3. **Persist long-term memory** for personal context and learning
4. **Be extended** with specialized sub-agents (e.g., Sal the coder, Steve the crypto-analyst) and new interfaces (Slack, GUI)

### Primary Development Goals
- Improve the developer's Python, Git, and system integration skills
- Develop a fully functional Jarvis-like assistant capable of executing system and API commands
- Build and extend Jarvis through daily modular feature additions using Claude Code CLI and Gemini Code CLI

---

## 2. High-Level Architecture

```mermaid
flowchart LR
    subgraph Agents
        J(Jarvis – General)
        Sal(Sal – Coding)
        Steve(Steve – Crypto)
    end
    subgraph MCP_Server
        Tools[API Endpoints & Tools]
    end
    subgraph Memory
        Chroma[(Chroma DB)]
        State[jarvis_state.json]
    end
    J --voice--> Whisper[Whisper (STT)]
    J --text--> LLM[LLM (OpenAI/Ollama)]
    LLM --text--> ElevenLabs[11 Labs (TTS)]
    J --> Tools
    Tools --> Chroma
    Tools --> State
```

---

## 3. Functional Requirements

### 3.1 Voice Interaction System

| Component | Technology/Service | Implementation Notes |
|-----------|-------------------|---------------------|
| **Speech-to-Text** | **Whisper** (local) | GPU-accelerated transcription using `faster-whisper` |
| **Language Model** | **OpenAI GPT-4o** (cloud) or **local Ollama model** | Switchable via endpoint parameter |
| **Text-to-Speech** | **ElevenLabs TTS API** | High-quality voice output with fallback to `pyttsx3` |
| **Wake Word** | Custom implementation | Background service listening for "Hey Jarvis" |

### 3.2 Core Toolset via MCP Server

| Category | Capability | Free-Tier API | Endpoint Path | Notes |
|----------|------------|--------------|---------------|-------|
| **Web Search** | Google search snippets | **SerpAPI** (100/mo) | `/search` | Real-time web information |
| **Weather** | Current + forecast | **OpenWeatherMap** (1k/day) | `/weather` | Location-based weather data |
| **Crypto Prices** | Spot prices & market data | **CoinGecko** (unlimited) | `/crypto` | Real-time crypto market data |
| **News** | Headlines & article search | **NewsAPI** (500/day) | `/news` | Current events and news |
| **Email** | Send/read Gmail | **Gmail API** | `/gmail` | OAuth 2 required |
| **Calendar** | Read/create events | **Google Calendar API** | `/calendar` | OAuth 2 required |
| **File Operations** | CRUD files & folders | Local OS | `/fs/*` | Secure local file management |
| **System Control** | Restricted shell commands | Local OS | `/system/*` | Volume, brightness, apps |

All endpoints share a common JSON schema and API-key authentication.

### 3.3 Memory Management System

| Memory Layer | Description | Storage Technology | Collection Name |
|-------------|-------------|-------------------|----------------|
| **Conversation Embeddings** | Full transcript of every session embedded & stored as vectors for long-term context retrieval | **ChromaDB** | `conversations` |
| **Structured Facts (KV)** | Auto-extracted facts (name, locale, preferences) with metadata `{value, convo_id, timestamp, summary}` | **ChromaDB** | `facts` |
| **Session State** | Goals, todo list, log of actions, current task ownership | **JSON file** | `jarvis_state.json` |
| **Metadata** | `convo_id`, datetime, short summary, speaker role | Embedded with records | N/A |

**Maintenance Tasks**: Periodic cleaning, re-indexing, and compression of old embeddings.

### 3.4 Modularity & Extensibility
- **LangChain** orchestrates agent logic, tool routing, and memory management
- All external integrations live on the MCP server – adding tools never alters agent code
- Future specialized agents reuse the same MCP endpoints and memory systems
- Plugin architecture for custom tools and integrations

---

## 4. Development Phases

### 🔰 Phase 1: MVP (Bare Bones Jarvis)

**Core Features:**
- ✅ Voice input via local Whisper with GPU acceleration
- ✅ Basic voice command recognition ("open browser", "what time is it")
- ✅ Voice output using ElevenLabs API
- ✅ Shared JSON state file (`jarvis_state.json`) for session management
- ✅ Modular codebase with clear documentation
- ✅ Local Git repo with proper structure and `.gitignore`

**File Structure:**
```
jarvis-voice-assistant/
├── main.py                 # Main application entry point
├── config.py              # Configuration management
├── voice_input.py         # Whisper STT integration
├── command_parser.py      # Natural language command parsing
├── elevenlabs_output.py   # TTS output handling
├── memory/
│   ├── chroma_manager.py  # ChromaDB integration
│   └── state_manager.py  # JSON state management
├── mcp_server/           # MCP server implementation
│   ├── server.py         # FastAPI server
│   ├── tools/           # Individual tool implementations
│   └── schemas/         # API schemas and models
├── agents/              # Agent implementations
├── logs/               # Application logs
├── jarvis_state.json   # Session state
├── requirements.txt    # Python dependencies
└── README.md          # Project documentation
```

### 🚀 Phase 2: Intermediate Features

**Conversational Capabilities:**
- Enhanced memory with ChromaDB vector store
- Context tracking and recall from prior sessions
- Personality development through memory and reflection logs

**Tool & API Integrations:**
- Complete MCP server with all planned endpoints
- Weather, news, crypto, and web search integration
- Gmail and Google Calendar connectivity
- File summarization (PDF, DOCX, TXT via voice)
- Advanced system automation capabilities

**System Automation:**
- Application control via voice commands
- File system cleanup and organization
- Voice macros for gaming and productivity
- System settings control (brightness, volume, etc.)

### 🧠 Phase 3: Advanced Intelligence & Autonomy

**Planning & Organization:**
- Self-generated daily task plans
- Standup assistant functionality
- Automated feature reviews and documentation
- Changelog generation and project tracking

**Visual Context & Copilot Mode:**
- Background service with always-on listening
- Screenshot capture and analysis on demand
- OCR and visual context understanding
- Application-specific contextual help

**Learning & Development Tools:**
- AI agent contribution tracking
- Code explanation and documentation generation
- Live debugging assistance
- Reflective mode for process improvement

---

## 5. Non-Functional Requirements

### Performance
- **Response Time**: < 200ms average round-trip for common queries on local GPU
- **Memory Usage**: Efficient ChromaDB indexing with periodic cleanup
- **Concurrent Handling**: Support for multiple simultaneous tool requests

### Security & Privacy
- **Local-First**: All private data stored on user's machine
- **API Security**: Keys stored in `.env` files, never logged or transmitted
- **Data Encryption**: Optional encryption for memory and state files
- **Kill Switch**: Emergency "shut everything down" command

### Quality & Reliability
- **Logging**: Structured JSON logs per component with rotation
- **Testing**: PyTest with minimum 80% coverage requirement
- **Error Handling**: Graceful degradation and recovery mechanisms
- **Documentation**: Comprehensive inline and external documentation

---

## 6. Technology Stack

### Core Technologies
- **Python 3.11+** - Primary development language
- **LangChain** - Agent orchestration and memory management
- **FastAPI** - MCP server implementation
- **ChromaDB** - Vector database for embeddings
- **Whisper** - Local speech-to-text processing

### Development Tools
- **VS Code** - Primary IDE with extensions
- **Git/GitHub** - Version control and collaboration
- **Claude Code CLI** - Primary AI development assistant
- **Gemini Code CLI** - Secondary AI development assistant

### Deployment Target
- **Ubuntu 22.04** workstation
- **Intel i9** processor
- **Dual RTX 3090** GPUs for ML acceleration

---

## 7. External API References

| Service | Documentation URL | Authentication | Rate Limits | Notes |
|---------|------------------|---------------|-------------|-------|
| **Gmail API** | https://developers.google.com/workspace/gmail/api/quickstart/python | OAuth 2.0 | 1B quota units/day | Email integration |
| **Google Calendar API** | https://developers.google.com/workspace/calendar/api/quickstart/python | OAuth 2.0 | 1M requests/day | Calendar management |
| **SerpAPI** | https://serpapi.com/ | API Key | 100 searches/month (free) | Web search |
| **OpenWeatherMap** | https://openweathermap.org/api | API Key | 1,000 calls/day (free) | Weather data |
| **CoinGecko** | https://docs.coingecko.com/ | None | Unlimited (free tier) | Crypto prices |
| **NewsAPI** | https://newsapi.org/docs | API Key | 500 requests/day (free) | News headlines |
| **ElevenLabs TTS** | https://elevenlabs.io/docs/capabilities/text-to-speech | API Key | 10k characters/month (free) | Voice synthesis |
| **Whisper** | https://github.com/openai/whisper | None | N/A | MIT license, fully local |

---

## 8. Acceptance Criteria

### MVP Acceptance Criteria
- **AC-1**: User can say "What's the weather?" and receive a spoken reply with current conditions
- **AC-2**: User can ask "What's BTC price?" and get the latest Bitcoin value
- **AC-3**: Jarvis remembers user's stated preferences (favorite coffee, location) across sessions
- **AC-4**: Switching LLM endpoint from OpenAI to local model requires only configuration change
- **AC-5**: All MCP server tools are accessible via `/health` endpoint returning HTTP 200

### Extended Acceptance Criteria
- **AC-6**: User can dictate and send emails through voice commands
- **AC-7**: Jarvis can schedule calendar appointments via natural language requests
- **AC-8**: System responds to wake word "Hey Jarvis" from background service
- **AC-9**: All conversations are persistently stored and searchable through natural language
- **AC-10**: Emergency shutdown command immediately terminates all Jarvis processes

---

## 9. Development Philosophy & Guidelines

### Code Quality Standards
- **Explanation Requirement**: Claude and Gemini must explain all generated code line-by-line
- **Git Workflow**: Each feature requires clean commit messages and proper branching
- **State Management**: All changes must update `jarvis_state.json` with status tracking
- **Documentation**: Inline comments and external docs for all major components

### Incremental Development Approach
1. **Daily Feature Addition**: Small, testable increments with immediate value
2. **Collaborative Development**: Leverage both Claude Code CLI and Gemini Code CLI
3. **Learning Focus**: Each implementation should teach new Python/system integration concepts
4. **Testing First**: Write tests before implementation when possible

---

## 10. Future Roadmap

### Phase 4: Multi-Modal Expansion
1. **Slack Bot** interface with chat and slash commands
2. **Web-based Dashboard** for settings and conversation history
3. **Mobile Companion App** for remote Jarvis access
4. **Desktop GUI** for visual interaction and settings management

### Phase 5: Specialized Agent Ecosystem
1. **Sal the Coder** - Specialized programming assistant
2. **Steve the Crypto-Analyst** - Market analysis and trading insights
3. **Custom Agent Builder** - Framework for creating domain-specific agents
4. **Agent Marketplace** - Community-driven agent sharing platform

### Phase 6: Advanced Capabilities
1. **Computer Vision** - Screenshot analysis and visual understanding
2. **Process Automation** - Complex multi-step task automation
3. **Learning Optimization** - Self-improving algorithms and personalization
4. **Enterprise Integration** - Business tool connectivity and workflow automation

---

## 11. Success Metrics

### Technical Metrics
- **System Uptime**: >99% availability during active use
- **Response Accuracy**: >95% correct interpretation of voice commands
- **Memory Retention**: 100% persistence of important user information
- **API Reliability**: <1% failure rate for external service calls

### User Experience Metrics
- **Voice Recognition**: <5% transcription errors in normal conditions
- **Task Completion**: >90% successful completion of requested tasks
- **User Satisfaction**: Measured through daily interaction logs and feedback
- **Learning Effectiveness**: Demonstrated improvement in Python and system skills

---

*End of Comprehensive Product Requirements Document*

