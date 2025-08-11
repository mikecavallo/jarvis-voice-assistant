# API Keys Setup for Jarvis Assistant

This document explains how to set up API keys for Jarvis Assistant functionality.

## Environment Setup

1. **Create .env file**: Copy the structure below and add your actual API keys
2. **Never commit .env files**: They are ignored by git for security
3. **Generate secure keys**: Use the commands provided below

## Required Environment Variables

Create a `.env` file in the root directory with these variables:

```bash
# ElevenLabs TTS API Key - Get from: https://elevenlabs.io/
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# OpenWeatherMap API Key - Get from: https://openweathermap.org/api  
OPENWEATHER_API_KEY=your_openweather_api_key_here

# SerpAPI Key for web search - Get from: https://serpapi.com/
SERPAPI_KEY=your_serpapi_key_here

# NewsAPI Key - Get from: https://newsapi.org/
NEWS_API_KEY=your_newsapi_key_here

# MCP Server API Key (generate random secure key)
# Generate with: python -c "import secrets; print('jarvis-mcp-' + secrets.token_urlsafe(32))"
MCP_API_KEY=jarvis-mcp-YOUR_GENERATED_KEY_HERE

# Optional: OpenAI API Key for advanced LLM features
# OPENAI_API_KEY=your_openai_api_key_here
```

## API Key Setup Instructions

### ElevenLabs (Text-to-Speech)
1. Sign up at https://elevenlabs.io/
2. Go to Profile Settings → API Key
3. Generate and copy your API key
4. Add to .env: `ELEVENLABS_API_KEY=your_key_here`

### OpenWeatherMap (Weather Data)
1. Sign up at https://openweathermap.org/api
2. Go to API keys section in your account
3. Copy the default API key
4. Add to .env: `OPENWEATHER_API_KEY=your_key_here`

### SerpAPI (Web Search)
1. Sign up at https://serpapi.com/
2. Copy your API key from the dashboard
3. Add to .env: `SERPAPI_KEY=your_key_here`

### NewsAPI (News Data)
1. Sign up at https://newsapi.org/
2. Click 'Get API Key' and register
3. Copy your API key
4. Add to .env: `NEWS_API_KEY=your_key_here`

### MCP Server Key (Internal Security)
Generate a secure random key:
```bash
python -c "import secrets; print('jarvis-mcp-' + secrets.token_urlsafe(32))"
```
Add to .env: `MCP_API_KEY=jarvis-mcp-[generated_key]`

## Google OAuth2 Setup

For Gmail and Calendar integration:
1. Run: `python setup_google_credentials.py`
2. Follow the OAuth2 flow to authenticate
3. Credentials are stored securely in `credentials/` directory

## Testing API Keys

Run the setup script to verify all keys:
```bash
python setup_api_keys.py
```

## Security Notes

- ✅ Never commit `.env` files to version control
- ✅ Use strong, randomly generated keys where possible
- ✅ Regularly rotate API keys for security
- ✅ Monitor API usage for unusual activity
- ❌ Never hardcode API keys in source code
- ❌ Never share API keys in public channels