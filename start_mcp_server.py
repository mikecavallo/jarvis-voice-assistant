#!/usr/bin/env python3
"""
MCP Server startup script for Jarvis Assistant.

This script starts the FastAPI MCP server that provides external tool access
for Jarvis. Run this before starting the main Jarvis assistant.

Usage:
    python start_mcp_server.py [--host HOST] [--port PORT]
"""

import argparse
import os

import uvicorn
from dotenv import load_dotenv

from mcp_server import app

load_dotenv()  # so MCP_HOST / MCP_PORT from .env apply to the argparse defaults

def main():
    parser = argparse.ArgumentParser(description="Start Jarvis MCP Server")
    parser.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"), help="Host to bind to")
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "8000")), help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    print("🚀 Starting Jarvis MCP Server...")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   Reload: {args.reload}")
    print()
    print("🔧 Available endpoints:")
    print("   GET  /health - Health check")
    print("   POST /mcp - Main MCP endpoint") 
    print("   GET  /search - Web search")
    print("   GET  /weather - Weather data")
    print("   GET  /crypto - Crypto prices")
    print("   GET  /news - News headlines")
    print()
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main()