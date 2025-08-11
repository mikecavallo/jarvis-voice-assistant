#!/bin/bash

# Jarvis Voice Assistant Startup Script
# This script ensures all necessary components are running before starting Jarvis

set -e  # Exit on any error
set -o pipefail  # Exit on pipe failures

# Suppress audio warnings at system level
export PULSE_RUNTIME_PATH="/dev/null"
export ALSA_PCM_CARD=0
export ALSA_PCM_DEVICE=0
export PYGAME_HIDE_SUPPORT_PROMPT=1
export ANONYMIZED_TELEMETRY=False
# Redirect ALSA error messages to null
exec 3>&2 2>/dev/null

echo "🤖 Starting Jarvis Voice Assistant..."
echo "============================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to detect audio devices and suppress warnings
setup_audio_environment() {
    echo -e "${YELLOW}🔊 Configuring audio environment...${NC}"
    
    # Create ALSA config to suppress warnings
    mkdir -p ~/.config/alsa
    cat > ~/.config/alsa/asoundrc << EOF
pcm.!default {
    type pulse
}
ctl.!default {
    type pulse
}
EOF
    
    # Test audio device availability
    if command -v pactl >/dev/null 2>&1; then
        if pactl list short sinks >/dev/null 2>&1; then
            echo -e "${GREEN}✅ PulseAudio detected and configured${NC}"
        else
            echo -e "${YELLOW}⚠️  PulseAudio not running, using ALSA fallback${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Using ALSA audio system${NC}"
    fi
    
    # Export additional audio suppression variables
    export SDL_AUDIODRIVER=pulse
    export PULSE_RUNTIME_PATH="${XDG_RUNTIME_DIR}/pulse"
    
    # Restore stderr for our script output
    exec 2>&3 3>&-
}

# Function to start MCP server with health checks
start_mcp_server() {
    echo -e "${YELLOW}🔧 Starting MCP Server...${NC}"
    
    # Kill any existing MCP server processes gracefully
    if pgrep -f "python -m mcp_server.server" >/dev/null; then
        echo -e "${YELLOW}⏳ Stopping existing MCP server...${NC}"
        pkill -f "python -m mcp_server.server" 2>/dev/null || true
        sleep 3
        
        # Force kill if still running
        if pgrep -f "python -m mcp_server.server" >/dev/null; then
            pkill -9 -f "python -m mcp_server.server" 2>/dev/null || true
            sleep 1
        fi
    fi
    
    # Check if port 8000 is still in use by another service
    if check_port 8000; then
        echo -e "${RED}❌ Port 8000 is still in use by another service:${NC}"
        lsof -Pi :8000 -sTCP:LISTEN
        echo -e "${RED}Please stop the service using port 8000 or change the MCP server port.${NC}"
        exit 1
    fi
    
    # Start MCP server with proper logging
    echo -e "${YELLOW}⏳ Starting MCP server...${NC}"
    python -m mcp_server.server > mcp_server.log 2>&1 &
    MCP_PID=$!
    echo $MCP_PID > .mcp_server.pid
    
    # Wait for server to start with better feedback
    for i in {1..15}; do
        if check_port 8000; then
            # Test server health endpoint
            if command -v curl >/dev/null 2>&1; then
                if curl -s -f "http://localhost:8000/health" >/dev/null 2>&1; then
                    echo -e "${GREEN}✅ MCP Server started and healthy (PID: $MCP_PID)${NC}"
                    return 0
                fi
            else
                echo -e "${GREEN}✅ MCP Server started successfully (PID: $MCP_PID)${NC}"
                return 0
            fi
        fi
        
        # Show progress dots
        printf "."
        sleep 1
    done
    
    echo -e "\n${RED}❌ MCP Server failed to start properly${NC}"
    echo -e "${YELLOW}Check mcp_server.log for details:${NC}"
    tail -10 mcp_server.log 2>/dev/null || echo "No log file found"
    exit 1
}

# Function to check virtual environment
check_venv() {
    if [[ "$VIRTUAL_ENV" == *"jarvis_env"* ]]; then
        echo -e "${GREEN}✅ Virtual environment activated: jarvis_env${NC}"
    else
        echo -e "${YELLOW}⚠️  Activating jarvis_env virtual environment...${NC}"
        source jarvis_env/bin/activate
        if [[ "$VIRTUAL_ENV" == *"jarvis_env"* ]]; then
            echo -e "${GREEN}✅ Virtual environment activated successfully${NC}"
        else
            echo -e "${RED}❌ Failed to activate virtual environment${NC}"
            exit 1
        fi
    fi
}

# Function to check environment variables with detailed validation
check_env() {
    if [ ! -f ".env" ]; then
        echo -e "${RED}❌ .env file not found.${NC}"
        if [ -f ".env.template" ]; then
            echo -e "${YELLOW}🔧 Found .env.template. Creating .env file...${NC}"
            cp .env.template .env
            echo -e "${YELLOW}⚠️  Please edit .env file with your API keys before continuing.${NC}"
            echo -e "${YELLOW}   Required: MCP_API_KEY (generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\")${NC}"
            echo -e "${YELLOW}   Optional: ELEVENLABS_API_KEY, OPENWEATHER_API_KEY, etc.${NC}"
            exit 1
        else
            echo -e "${RED}Please create .env file from .env.template${NC}"
            exit 1
        fi
    fi
    
    # Source the .env file with error handling
    set -a
    if ! source .env; then
        echo -e "${RED}❌ Error loading .env file. Please check for syntax errors.${NC}"
        exit 1
    fi
    set +a
    
    # Validate critical environment variables
    missing_vars=()
    
    if [ -z "$MCP_API_KEY" ] || [ "$MCP_API_KEY" = "CHANGE_ME_TO_SECURE_RANDOM_KEY" ]; then
        missing_vars+=("MCP_API_KEY (generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))')")
    fi
    
    # Optional but recommended variables
    optional_vars=()
    [ -z "$ELEVENLABS_API_KEY" ] && optional_vars+=("ELEVENLABS_API_KEY (for voice output)")
    [ -z "$OPENWEATHER_API_KEY" ] && optional_vars+=("OPENWEATHER_API_KEY (for weather commands)")
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo -e "${RED}❌ Missing required environment variables:${NC}"
        printf '   %s\n' "${missing_vars[@]}"
        exit 1
    fi
    
    if [ ${#optional_vars[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Optional environment variables not set:${NC}"
        printf '   %s\n' "${optional_vars[@]}"
        echo -e "${YELLOW}   Some features may be limited.${NC}"
    fi
    
    echo -e "${GREEN}✅ Environment variables validated${NC}"
}

# Main startup sequence
echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"

# Check if we're in the correct directory
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ main.py not found. Please run this script from the jarvis-voice-assistant directory${NC}"
    exit 1
fi

# Check virtual environment
check_venv

# Setup audio environment (suppress ALSA warnings)
setup_audio_environment

# Check environment variables
check_env

# Start MCP server
start_mcp_server

echo -e "${GREEN}✅ All systems ready!${NC}"
echo -e "${YELLOW}🎤 Starting Jarvis Voice Assistant...${NC}"
echo "============================================"

# Start Jarvis with mode argument if provided (using quiet wrapper)
if [ "$1" ]; then
    python run_quiet.py python main.py "$1"
else
    python run_quiet.py python main.py
fi

# Enhanced cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up...${NC}"
    
    # Stop MCP server gracefully
    if [ -f ".mcp_server.pid" ]; then
        MCP_PID=$(cat .mcp_server.pid)
        if kill -0 $MCP_PID 2>/dev/null; then
            echo -e "${YELLOW}   Stopping MCP server (PID: $MCP_PID)...${NC}"
            kill $MCP_PID 2>/dev/null || true
            sleep 2
            # Force kill if still running
            if kill -0 $MCP_PID 2>/dev/null; then
                kill -9 $MCP_PID 2>/dev/null || true
            fi
        fi
        rm -f .mcp_server.pid
    else
        # Fallback to process name killing
        pkill -f "python -m mcp_server.server" 2>/dev/null || true
    fi
    
    # Clean up any temporary files
    rm -f .jarvis_startup.lock 2>/dev/null || true
    
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Set up signal handlers
trap cleanup EXIT
trap 'echo -e "\n${YELLOW}🛑 Interrupted by user${NC}"; cleanup; exit 130' INT TERM