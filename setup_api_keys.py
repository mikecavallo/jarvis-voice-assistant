#!/usr/bin/env python3
"""
API Keys Setup Guide for Jarvis MCP Server.

This script provides detailed instructions for obtaining API keys
for each MCP server tool and helps set up the .env file.
"""

import os
from pathlib import Path

API_SERVICES = {
    "openweather": {
        "name": "OpenWeatherMap",
        "env_var": "OPENWEATHER_API_KEY",
        "url": "https://openweathermap.org/api",
        "free_tier": "1,000 API calls/day",
        "signup_steps": [
            "1. Go to https://openweathermap.org/api",
            "2. Click 'Sign Up' and create a free account",
            "3. Verify your email address",
            "4. Go to 'API keys' section in your account",
            "5. Copy the default API key (starts with a letter)",
            "6. Add to .env as: OPENWEATHER_API_KEY=your_key_here"
        ],
        "test_command": "curl 'http://api.openweathermap.org/data/2.5/weather?q=London&appid=YOUR_KEY'"
    },
    "serpapi": {
        "name": "SerpAPI (Google Search)",
        "env_var": "SERPAPI_KEY", 
        "url": "https://serpapi.com/",
        "free_tier": "100 searches/month",
        "signup_steps": [
            "1. Go to https://serpapi.com/",
            "2. Click 'Sign Up' for free account",
            "3. Verify your email address",
            "4. Go to your Dashboard",
            "5. Copy your API key from the dashboard",
            "6. Add to .env as: SERPAPI_KEY=your_key_here"
        ],
        "test_command": "curl 'https://serpapi.com/search.json?q=Python&api_key=YOUR_KEY'"
    },
    "newsapi": {
        "name": "NewsAPI",
        "env_var": "NEWS_API_KEY",
        "url": "https://newsapi.org/",
        "free_tier": "1,000 requests/day",
        "signup_steps": [
            "1. Go to https://newsapi.org/",
            "2. Click 'Get API Key' and sign up",
            "3. Verify your email address", 
            "4. Go to your account dashboard",
            "5. Copy your API key",
            "6. Add to .env as: NEWS_API_KEY=your_key_here"
        ],
        "test_command": "curl 'https://newsapi.org/v2/top-headlines?country=us&apiKey=YOUR_KEY'"
    },
    "elevenlabs": {
        "name": "ElevenLabs (Text-to-Speech)",
        "env_var": "ELEVENLABS_API_KEY",
        "url": "https://elevenlabs.io/",
        "free_tier": "10,000 characters/month",
        "signup_steps": [
            "1. Go to https://elevenlabs.io/",
            "2. Click 'Sign Up' for free account",
            "3. Complete the onboarding process",
            "4. Go to Profile Settings > API Key",
            "5. Generate and copy your API key",
            "6. Add to .env as: ELEVENLABS_API_KEY=your_key_here"
        ],
        "test_command": "curl -X POST 'https://api.elevenlabs.io/v1/voices' -H 'xi-api-key: YOUR_KEY'"
    }
}

def print_header():
    """Print script header."""
    print("🔑 Jarvis MCP Server - API Keys Setup Guide")
    print("=" * 60)
    print("This guide will help you set up API keys for all MCP server tools.")
    print("All services offer free tiers that are perfect for development and testing.")
    print()

def check_env_file():
    """Check if .env file exists and create if needed."""
    env_file = Path(".env")
    template_file = Path(".env.template")
    
    if not env_file.exists():
        if template_file.exists():
            print("📁 Creating .env file from template...")
            import shutil
            shutil.copy(template_file, env_file)
            print("✅ Created .env file")
        else:
            print("❌ No .env.template found. Creating basic .env file...")
            with open(env_file, 'w') as f:
                f.write("# Jarvis Assistant Environment Variables\n")
                f.write("# Add your API keys below\n\n")
                for service_id, service in API_SERVICES.items():
                    f.write(f"# {service['name']}\n")
                    f.write(f"{service['env_var']}=your_key_here\n\n")
            print("✅ Created basic .env file")
    else:
        print("✅ .env file already exists")
    
    return env_file

def check_existing_keys(env_file: Path):
    """Check which API keys are already configured."""
    print("\n🔍 Checking existing API key configuration...")
    
    # Load existing env vars
    env_vars = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    configured = []
    missing = []
    
    for service_id, service in API_SERVICES.items():
        env_var = service['env_var']
        value = env_vars.get(env_var, '').strip()
        
        if value and not value.startswith('your_') and not value.endswith('_here') and len(value) > 10:
            configured.append(service['name'])
            print(f"  ✅ {service['name']}: Configured")
        else:
            missing.append(service_id)
            print(f"  ❌ {service['name']}: Not configured")
    
    print(f"\n📊 Status: {len(configured)}/{len(API_SERVICES)} services configured")
    
    return configured, missing

def print_service_setup(service_id: str, service: dict):
    """Print setup instructions for a specific service."""
    print(f"\n🔧 {service['name']}")
    print("-" * 40)
    print(f"Website: {service['url']}")
    print(f"Free Tier: {service['free_tier']}")
    print(f"Environment Variable: {service['env_var']}")
    print()
    print("Setup Steps:")
    for step in service['signup_steps']:
        print(f"   {step}")
    print()
    print(f"Test Command:")
    print(f"   {service['test_command']}")
    print()

def print_priority_services():
    """Print information about which services are most important."""
    print("\n⭐ PRIORITY SERVICES")
    print("=" * 40)
    print("For basic MCP server functionality, prioritize these services:")
    print()
    
    priority_services = [
        ("openweather", "Weather information - very commonly used"),
        ("newsapi", "News headlines - good for testing and demos"),
        ("serpapi", "Web search - powerful but limited free tier"),
        ("elevenlabs", "Text-to-speech - needed for voice output")
    ]
    
    for service_id, description in priority_services:
        service = API_SERVICES[service_id]
        print(f"1. {service['name']}")
        print(f"   {description}")
        print(f"   Free: {service['free_tier']}")
        print()

def print_testing_instructions():
    """Print instructions for testing the setup."""
    print("\n🧪 TESTING YOUR SETUP")
    print("=" * 40)
    print("After adding your API keys:")
    print()
    print("1. Start the MCP server:")
    print("   python start_mcp_server.py")
    print()
    print("2. In another terminal, test the tools:")
    print("   python test_mcp_tools.py")
    print()
    print("3. For verbose output:")
    print("   python test_mcp_tools.py --verbose")
    print()
    print("4. Test specific server URL:")
    print("   python test_mcp_tools.py --server-url http://localhost:8001")

def main():
    """Main setup guide function."""
    print_header()
    
    # Check/create .env file
    env_file = check_env_file()
    
    # Check existing configuration
    configured, missing = check_existing_keys(env_file)
    
    if not missing:
        print("\n🎉 All API keys are configured!")
        print("Run 'python test_mcp_tools.py' to test your setup.")
        return
    
    # Show priority services
    print_priority_services()
    
    # Show setup instructions for missing services
    print("\n📋 SETUP INSTRUCTIONS")
    print("=" * 40)
    print("Here are the setup instructions for missing API keys:")
    
    for service_id in missing:
        service = API_SERVICES[service_id]
        print_service_setup(service_id, service)
    
    # Show testing instructions
    print_testing_instructions()
    
    print("\n💡 TIPS")
    print("=" * 40)
    print("• All these services offer generous free tiers")
    print("• You can start with just 1-2 services and add more later")
    print("• Keep your API keys secure and never commit them to git")
    print("• The MCP server will work with any subset of these services")
    print("• Tools without API keys will be marked as 'skipped' in tests")

if __name__ == "__main__":
    main()