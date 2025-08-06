# Jarvis Virtual Assistant – MVP Product Requirements Document  
*Generated 2025-08-05*

---

## 1 Vision & Scope  
Build a modular, voice‑first personal AI assistant (“**Jarvis**”) that can:  
1. Converse naturally through speech on the local machine (CLI).  
2. Access a central **MCP server** for all external tools & APIs.  
3. Persist long‑term memory for personal context.  
4. Be extended later with specialised sub‑agents (e.g. Sal the coder, Steve the crypto‑analyst) and new interfaces (Slack, GUI).

---

## 2 High‑Level Architecture  

```mermaid
flowchart LR
    subgraph Agents
        J(Jarvis – General)
        Sal(Sal – Coding)
        Steve(Steve – Crypto)
    end
    subgraph MCP_Server
        Tools[API Endpoints & Tools]
    end
    subgraph Memory
        Chroma[(Chroma DB)]
    end
    J --voice--> Whisper[Whisper (STT)]
    J --text--> LLM[LLM (OpenAI/Ollama)]
    LLM --text--> ElevenLabs[11 Labs (TTS)]
    J --> Tools
    Tools --> Chroma
```

---

## 3 Functional Requirements (MVP)

### 3.1 Console‑Based Voice Interaction  
| Component | Tech / Service | Notes |  
|-----------|----------------|-------|  
| Speech‑to‑Text | **Whisper** (local) | GPU‑accelerated transcription.  
| Language Model | **OpenAI GPT‑4o** *(cloud)* or **local Ollama model** | Switchable via endpoint param.  
| Text‑to‑Speech | **ElevenLabs TTS API** | High‑quality voice output.  

### 3.2 Core Toolset via MCP Server  
| Category | Capability | Free‑Tier API | Endpoint Path |  
|----------|------------|--------------|---------------|  
| Web Search | Google search snippets | **SerpAPI** (100 / mo) | `/search`  
| Weather | Current + forecast | **OpenWeatherMap** | `/weather`  
| Crypto Prices | Spot prices & market data | **CoinGecko** | `/crypto`  
| News | Top headlines & article search | **NewsAPI** | `/news`  
| Email | Send / read Gmail | **Gmail API** | `/gmail`  
| Calendar | Read / create events | **Google Calendar API** | `/calendar`  
| File Ops | Create / read / update / delete files & folders | Local OS | `/fs/*`  
| System | Run restricted shell commands | Local OS | `/system/*`  

All endpoints share a common JSON schema and API‑key auth.  

### 3.3 Memory Management  

| Layer | Description | Storage |  
|-------|-------------|---------|  
| **Conversation Embeddings** | Full transcript of every session embedded & stored as vectors for long‑term context retrieval. | **Chroma** collection `conversations` |  
| **Structured Facts (KV)** | Auto‑extracted facts (name, locale, prefs…) with metadata `{value, convo_id, timestamp, summary}`. | **Chroma** collection `facts` |  
| **Metadata** | `convo_id`, datetime, short summary, speaker role. | Stored with each record |  

Periodic maintenance tasks clean, re‑index and compress old embeddings.

### 3.4 Modularity & Extensibility  
* **LangChain** orchestrates agent logic, tool routing and memory.  
* All external integrations live on the MCP server – swapping or adding a tool never alters agent code.  
* Future agents simply reuse the same MCP endpoints.

---

## 4 Non‑Functional Requirements  
* **Local‑first**: All private data lives on the user’s machine.  
* **Security**: API keys stored in `.env` and never logged.  
* **Performance**: < 200 ms average round‑trip for common queries on local GPU.  
* **Logging**: Structured JSON logs per component.  
* **Testing**: PyTest with 80 % coverage minimum.  

---

## 5 Tech Stack  
* **Python 3.11**, **LangChain**, **FastAPI**, **ChromaDB**, **Faiss** (future).  
* Development: VS Code + Git + Claude Code CLI / Gemini Code CLI.  
* Deployment target: Ubuntu 22.04 workstation (Intel i9, dual RTX 3090).

---

## 6 Project Backlog / Future Work  
1. **Slack Bot** interface (chat + slash commands).  
2. Web‑based dashboard & settings GUI.  
3. Specialized sub‑agents with distinct personas.  
4. Screenshot context + screen control.  
5. Mobile companion app.

---

## 7 External API Reference  

| Service | Docs URL | Notes |  
|---------|---------|-------|  
| Gmail API | https://developers.google.com/workspace/gmail/api/quickstart/python | OAuth 2 required.  
| Google Calendar API | https://developers.google.com/workspace/calendar/api/quickstart/python | OAuth 2 required.  
| SerpAPI | https://serpapi.com/ | Free tier 100 searches/mo.  
| OpenWeatherMap | https://openweathermap.org/api | Free tier 1,000 calls/day.  
| CoinGecko | https://docs.coingecko.com/ | Unlimited free.  
| NewsAPI | https://newsapi.org/docs | 500 requests/day free.  
| ElevenLabs TTS | https://elevenlabs.io/docs/capabilities/text-to-speech | 10k chars/month free.  
| Whisper | https://github.com/openai/whisper | MIT licence, fully local.  

---

## 8 Acceptance Criteria  
* **AC‑1**: User can say “What’s the weather?” and receive a spoken reply.  
* **AC‑2**: User can ask “What’s BTC price?” and get the latest value.  
* **AC‑3**: Jarvis remembers user’s stated favourite coffee across sessions.  
* **AC‑4**: Switching LLM endpoint from OpenAI to local model requires only a config change.  
* **AC‑5**: All tools are reachable via MCP server `/health` endpoint returning 200.  

---

*End of Document*
