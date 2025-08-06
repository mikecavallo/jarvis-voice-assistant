"""
Memory management package for Jarvis Assistant.

This package provides persistent memory capabilities including:
- State management (JSON-based session state)
- Vector memory (ChromaDB for conversations and facts)
- Memory search and retrieval
"""

from .state_manager import jarvis_state
from .chroma_manager import chroma_manager

__all__ = ['jarvis_state', 'chroma_manager']