# Jarvis Voice Assistant - Development Task Runner
# This Makefile provides convenient commands for development tasks

.PHONY: help install setup start start-voice start-text start-test stop clean logs health check-deps test-audio dev-setup

# Default target
help: ## Show this help message
	@echo "Jarvis Voice Assistant - Development Commands"
	@echo "=============================================="
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make <target>\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  %-15s %s\n", $$1, $$2 } /^##@/ { printf "\n%s\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Setup Commands
install: ## Install Python dependencies in virtual environment
	@echo "🔧 Installing dependencies..."
	@if [ ! -d "jarvis_env" ]; then \
		echo "📦 Creating virtual environment..."; \
		python3 -m venv jarvis_env; \
	fi
	@echo "📥 Installing Python packages..."
	@./jarvis_env/bin/pip install --upgrade pip
	@./jarvis_env/bin/pip install -r requirements.txt
	@echo "✅ Installation complete!"

setup: ## Complete development environment setup
	@echo "🚀 Setting up Jarvis development environment..."
	@$(MAKE) install
	@echo "⚙️  Checking environment configuration..."
	@if [ ! -f ".env" ]; then \
		echo "📝 Creating .env file from template..."; \
		cp .env.example .env; \
		echo "⚠️  Please edit .env file with your API keys!"; \
		echo "   Generate MCP_API_KEY with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""; \
	else \
		echo "✅ .env file exists"; \
	fi
	@echo "🔐 Setting up credentials directory..."
	@mkdir -p credentials logs
	@echo "📋 Development environment ready!"
	@echo "   Next steps:"
	@echo "   1. Edit .env file with your API keys"
	@echo "   2. Run 'make start' to launch Jarvis"

dev-setup: ## Quick setup for development (dependencies + basic config)
	@$(MAKE) setup
	@echo "🔑 Generating secure MCP API key..."
	@python3 -c "import secrets; key=secrets.token_urlsafe(32); print(f'Generated key: {key}')" > .mcp_key.tmp
	@KEY=$$(cat .mcp_key.tmp | cut -d' ' -f3); \
	sed -i "s/MCP_API_KEY=CHANGE_ME_TO_SECURE_RANDOM_KEY/MCP_API_KEY=$$KEY/" .env
	@rm .mcp_key.tmp
	@echo "✅ MCP API key configured automatically!"

##@ Runtime Commands  
start: ## Start Jarvis (interactive mode selection)
	@echo "🤖 Starting Jarvis Voice Assistant..."
	@chmod +x start_jarvis.sh
	@./start_jarvis.sh

start-voice: ## Start Jarvis in voice mode
	@echo "🎤 Starting Jarvis in voice mode..."
	@chmod +x start_jarvis.sh
	@./start_jarvis.sh voice

start-text: ## Start Jarvis in text mode  
	@echo "💬 Starting Jarvis in text mode..."
	@chmod +x start_jarvis.sh
	@./start_jarvis.sh text

start-test: ## Run Jarvis system tests
	@echo "🧪 Running Jarvis system tests..."
	@chmod +x start_jarvis.sh
	@./start_jarvis.sh test

##@ Management Commands
stop: ## Stop all Jarvis processes
	@echo "🛑 Stopping Jarvis processes..."
	@pkill -f "python -m mcp_server.server" 2>/dev/null || true
	@pkill -f "python main.py" 2>/dev/null || true
	@rm -f .mcp_server.pid 2>/dev/null || true
	@echo "✅ All processes stopped"

restart: ## Restart Jarvis services
	@$(MAKE) stop
	@sleep 2
	@$(MAKE) start

clean: ## Clean up temporary files and logs
	@echo "🧹 Cleaning up..."
	@rm -f mcp_server.log .mcp_server.pid .jarvis_startup.lock
	@rm -rf __pycache__ */__pycache__ */*/__pycache__
	@rm -rf *.pyc */*.pyc */*/*.pyc
	@find . -name "*.tmp" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

##@ Monitoring Commands
logs: ## Show MCP server logs
	@echo "📋 MCP Server Logs:"
	@echo "===================="
	@if [ -f "mcp_server.log" ]; then \
		tail -f mcp_server.log; \
	else \
		echo "No log file found. Start Jarvis first."; \
	fi

health: ## Check system health
	@echo "🏥 Jarvis Health Check"
	@echo "====================="
	@echo "📁 Environment:"
	@if [ -d "jarvis_env" ]; then echo "  ✅ Virtual environment exists"; else echo "  ❌ Virtual environment missing"; fi
	@if [ -f ".env" ]; then echo "  ✅ Environment file exists"; else echo "  ❌ Environment file missing"; fi
	@echo ""
	@echo "🔧 Services:"
	@if pgrep -f "python -m mcp_server.server" >/dev/null; then \
		echo "  ✅ MCP Server running (PID: $$(pgrep -f 'python -m mcp_server.server'))"; \
	else \
		echo "  ❌ MCP Server not running"; \
	fi
	@if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then \
		echo "  ✅ Port 8000 listening"; \
	else \
		echo "  ❌ Port 8000 not listening"; \
	fi
	@echo ""
	@echo "🔊 Audio:"
	@if command -v pactl >/dev/null 2>&1 && pactl list short sinks >/dev/null 2>&1; then \
		echo "  ✅ PulseAudio detected"; \
	else \
		echo "  ⚠️  PulseAudio not available, using ALSA"; \
	fi

check-deps: ## Check if all dependencies are installed
	@echo "🔍 Checking dependencies..."
	@./jarvis_env/bin/python -c "import sys; import pkg_resources; [pkg_resources.require(line.strip()) for line in open('requirements.txt') if line.strip() and not line.startswith('#')]" 2>/dev/null && echo "✅ All dependencies satisfied" || echo "❌ Some dependencies missing - run 'make install'"

test-audio: ## Test audio system configuration
	@echo "🔊 Testing audio configuration..."
	@echo "🎤 Microphone test:"
	@if command -v arecord >/dev/null 2>&1; then \
		echo "  Recording 3 seconds of audio to test microphone..."; \
		timeout 3s arecord -f cd test_audio.wav 2>/dev/null || true; \
		if [ -f "test_audio.wav" ]; then \
			echo "  ✅ Microphone recording successful"; \
			rm -f test_audio.wav; \
		else \
			echo "  ❌ Microphone recording failed"; \
		fi; \
	else \
		echo "  ⚠️  arecord not available, skipping microphone test"; \
	fi
	@echo "🔊 Speaker test:"
	@if command -v speaker-test >/dev/null 2>&1; then \
		echo "  Testing speakers for 2 seconds..."; \
		timeout 2s speaker-test -t sine -f 1000 -l 1 >/dev/null 2>&1 || true; \
		echo "  ✅ Speaker test completed (did you hear a tone?)"; \
	else \
		echo "  ⚠️  speaker-test not available, skipping speaker test"; \
	fi

##@ Development Helpers
format: ## Format code with black (if available)
	@if command -v black >/dev/null 2>&1; then \
		echo "🎨 Formatting Python code..."; \
		black *.py */*.py 2>/dev/null || true; \
		echo "✅ Code formatting complete"; \
	else \
		echo "⚠️  black not installed, skipping formatting"; \
	fi

lint: ## Run basic linting (if flake8 available)  
	@if command -v flake8 >/dev/null 2>&1; then \
		echo "🔍 Running linter..."; \
		flake8 *.py */*.py --max-line-length=100 --ignore=E203,W503 2>/dev/null || true; \
	else \
		echo "⚠️  flake8 not installed, skipping linting"; \
	fi

backup: ## Create backup of important files
	@echo "💾 Creating backup..."
	@mkdir -p backups
	@tar -czf "backups/jarvis-backup-$$(date +%Y%m%d-%H%M%S).tar.gz" \
		--exclude="jarvis_env" \
		--exclude="__pycache__" \
		--exclude="*.pyc" \
		--exclude="memory/chroma_db" \
		--exclude="backups" \
		--exclude=".git" \
		.
	@echo "✅ Backup created in backups/ directory"

##@ Information Commands
status: ## Show current system status
	@echo "📊 Jarvis System Status"
	@echo "======================="
	@$(MAKE) health
	@echo ""
	@echo "📈 Resource Usage:"
	@if pgrep -f "python -m mcp_server.server" >/dev/null; then \
		ps -p $$(pgrep -f "python -m mcp_server.server") -o pid,pcpu,pmem,cmd --no-headers | head -1 | awk '{printf "  MCP Server: PID %s, CPU %.1f%%, Memory %.1f%%\n", $$1, $$2, $$3}'; \
	fi

info: ## Show project information
	@echo "ℹ️  Jarvis Voice Assistant"
	@echo "========================="
	@echo "📁 Project: $$(pwd)"
	@echo "🐍 Python: $$(./jarvis_env/bin/python --version 2>/dev/null || echo 'Not available')"
	@echo "📦 Virtual Env: jarvis_env"
	@echo "🌐 MCP Server: http://localhost:8000"
	@echo ""
	@echo "📋 Available commands: make help"