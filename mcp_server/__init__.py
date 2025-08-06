"""
MCP Server package for Jarvis Assistant.

This package implements the Model Context Protocol server that provides
a centralized interface for all external tools and APIs.
"""

from .server import app

__all__ = ['app']